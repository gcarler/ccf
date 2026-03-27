from __future__ import annotations

import json
import hashlib
import csv
import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from backend import models
from backend.auth import VALID_ROLES
from backend.auth import require_active_user, require_admin
from backend.core.rate_limit import rate_limiter


router = APIRouter(prefix="/workspace", tags=["workspace"])

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FLAGS_FILE = DATA_DIR / "feature_flags.json"
AUDIT_FILE = DATA_DIR / "feature_flags_audit.ndjson"
INCIDENTS_FILE = DATA_DIR / "feature_flags_incidents.json"
NOTIFICATIONS_FILE = DATA_DIR / "feature_flags_notifications.ndjson"
SNAPSHOT_HISTORY_FILE = DATA_DIR / "feature_flags_snapshot_history.ndjson"

DEFAULT_WORKSPACE_CONFIG: Dict[str, Any] = {
    "features_enabled": {
        "command_center": True,
        "knowledge_graph": True,
        "web_vitals_dashboard": True,
        "automation_builder": False,
        "collaborative_editor": False,
        "presence_live": False,
    },
    "ui_theme_config": {
        "density": "comfortable",
        "accent": "blue",
    },
    "navigation_schema": [],
    "feature_rules": {
        "knowledge_graph": {
            "roles_allow": [],
            "roles_deny": [],
            "users_allow": [],
            "users_deny": [],
            "rollout_percent": 100,
        },
        "web_vitals_dashboard": {
            "roles_allow": ["admin", "coordinador"],
            "roles_deny": [],
            "users_allow": [],
            "users_deny": [],
            "rollout_percent": 100,
        },
    },
    "compliance_policy": {},
}

MAX_LIST_ITEMS = 200
MAX_USER_REF_LENGTH = 120
ALLOWED_RULE_KEYS = {"roles_allow", "roles_deny", "users_allow", "users_deny", "rollout_percent"}
SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}
COMPLIANCE_SNAPSHOT_SCHEMA_VERSION = "1.0.0"
CRITICAL_FEATURE_FLAGS = {
    "command_center",
    "knowledge_graph",
    "web_vitals_dashboard",
    "automation_builder",
    "collaborative_editor",
    "presence_live",
}

DEFAULT_COMPLIANCE_POLICY: Dict[str, Any] = {
    "active_environment": "production",
    "environments": {
        "development": {
            "incident_spike_delta": 10,
            "mtta_regression_pct": 0.5,
            "mttr_regression_pct": 0.5,
            "critical_feature_change_count_high": 3,
            "critical_feature_disabled_force": True,
        },
        "staging": {
            "incident_spike_delta": 7,
            "mtta_regression_pct": 0.35,
            "mttr_regression_pct": 0.35,
            "critical_feature_change_count_high": 2,
            "critical_feature_disabled_force": True,
        },
        "production": {
            "incident_spike_delta": 5,
            "mtta_regression_pct": 0.25,
            "mttr_regression_pct": 0.25,
            "critical_feature_change_count_high": 2,
            "critical_feature_disabled_force": True,
        },
    },
    "critical_feature_flags": sorted(CRITICAL_FEATURE_FLAGS),
    "suppressions": [],
}

DEFAULT_WORKSPACE_CONFIG["compliance_policy"] = DEFAULT_COMPLIANCE_POLICY


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
            data_envs = data_policy.get("environments", {}) if isinstance(data_policy, dict) else {}
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
                        *list((data_policy.get("critical_feature_flags") if isinstance(data_policy, dict) else []) or []),
                    }
                ),
                "suppressions": list((data_policy.get("suppressions") if isinstance(data_policy, dict) else []) or []),
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
    except Exception:
        return DEFAULT_WORKSPACE_CONFIG
    return DEFAULT_WORKSPACE_CONFIG


def _save_workspace_config(config: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FLAGS_FILE.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")


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


def _append_audit_event(event: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        **event,
    }
    with AUDIT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + "\n")


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


def _json_canonical(data: Any) -> str:
    return json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _snapshot_hash(snapshot: Dict[str, Any]) -> str:
    return hashlib.sha256(_json_canonical(snapshot).encode("utf-8")).hexdigest()


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
    with SNAPSHOT_HISTORY_FILE.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(_json_canonical(row) + "\n")


def _find_snapshot_history_item(rows: list[Dict[str, Any]], snapshot_id: str) -> Dict[str, Any] | None:
    return next((row for row in reversed(rows) if str(row.get("snapshot_id", "")) == snapshot_id), None)


def _verify_snapshot_history_item(item: Dict[str, Any]) -> Dict[str, Any]:
    snapshot = item.get("snapshot")
    signature = item.get("signature") or {}
    if not isinstance(snapshot, dict):
        return {"ok": False, "reason": "missing_snapshot_payload"}

    unsigned = dict(snapshot)
    unsigned.pop("signature", None)
    computed = _snapshot_hash(unsigned)
    expected = str(signature.get("hash") or "")
    return {
        "ok": bool(expected and computed == expected),
        "algorithm": str(signature.get("algorithm") or "sha256"),
        "expected_hash": expected,
        "computed_hash": computed,
    }


def _snapshot_metrics(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    audit = snapshot.get("audit") or {}
    anomalies = audit.get("anomalies") or {}
    incidents = snapshot.get("incidents") or {}
    summary = incidents.get("summary") or {}
    severity_counts = summary.get("severity_counts") or {}

    return {
        "audit_count": audit.get("count"),
        "has_anomaly": anomalies.get("has_anomaly"),
        "incident_count": incidents.get("count"),
        "critical_incidents": severity_counts.get("critical", 0),
        "high_incidents": severity_counts.get("high", 0),
        "mtta_minutes": summary.get("mtta_minutes"),
        "mttr_minutes": summary.get("mttr_minutes"),
    }


def _resolve_compliance_policy(
    policy: Dict[str, Any] | None = None,
    *,
    environment: str | None = None,
) -> Dict[str, Any]:
    source = policy if isinstance(policy, dict) else DEFAULT_COMPLIANCE_POLICY
    env_name = (environment or source.get("active_environment") or "production").strip().lower()
    envs = source.get("environments") if isinstance(source.get("environments"), dict) else {}
    env_policy = envs.get(env_name) if isinstance(envs.get(env_name), dict) else {}
    if not env_policy and env_name != "production":
        env_policy = envs.get("production") if isinstance(envs.get("production"), dict) else {}

    suppressions_raw = source.get("suppressions") if isinstance(source.get("suppressions"), list) else []
    suppressions = []
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    for item in suppressions_raw:
        if not isinstance(item, dict):
            continue
        expires_at = _parse_timestamp(item.get("expires_at"))
        if expires_at and expires_at.timestamp() <= now_ts:
            continue
        suppressions.append(item)

    critical_flags = source.get("critical_feature_flags")
    critical_flag_set = {
        str(flag).strip()
        for flag in (critical_flags if isinstance(critical_flags, list) else sorted(CRITICAL_FEATURE_FLAGS))
        if str(flag).strip()
    }
    if not critical_flag_set:
        critical_flag_set = set(CRITICAL_FEATURE_FLAGS)

    return {
        "environment": env_name,
        "incident_spike_delta": max(1, int(env_policy.get("incident_spike_delta", 5))),
        "mtta_regression_pct": max(0.01, float(env_policy.get("mtta_regression_pct", 0.25))),
        "mttr_regression_pct": max(0.01, float(env_policy.get("mttr_regression_pct", 0.25))),
        "critical_feature_change_count_high": max(1, int(env_policy.get("critical_feature_change_count_high", 2))),
        "critical_feature_disabled_force": bool(env_policy.get("critical_feature_disabled_force", True)),
        "critical_feature_flags": sorted(critical_flag_set),
        "suppressions": suppressions,
    }


def _is_drift_signal_suppressed(signal_type: str, signal_value: str, suppressions: list[Dict[str, Any]]) -> bool:
    normalized_type = signal_type.strip().lower()
    normalized_value = signal_value.strip().lower()
    for item in suppressions:
        kind = str(item.get("kind") or "").strip().lower()
        value = str(item.get("value") or "").strip().lower()
        if kind == "all":
            return True
        if kind == normalized_type and (not value or value == normalized_value):
            return True
    return False


def _compare_snapshot_payloads(
    base: Dict[str, Any],
    target: Dict[str, Any],
    *,
    policy: Dict[str, Any] | None = None,
    environment: str | None = None,
) -> Dict[str, Any]:
    base_metrics = _snapshot_metrics(base)
    target_metrics = _snapshot_metrics(target)

    metric_delta: Dict[str, Any] = {}
    for key in set(base_metrics.keys()) | set(target_metrics.keys()):
        before = base_metrics.get(key)
        after = target_metrics.get(key)
        delta = None
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            delta = round(float(after) - float(before), 2)
        metric_delta[key] = {"before": before, "after": after, "delta": delta}

    base_features = (base.get("config") or {}).get("features_enabled") or {}
    target_features = (target.get("config") or {}).get("features_enabled") or {}
    feature_changes = []
    for key in sorted(set(base_features.keys()) | set(target_features.keys())):
        before = base_features.get(key)
        after = target_features.get(key)
        if before == after:
            continue
        feature_changes.append({"feature": key, "before": before, "after": after})

    effective_policy = _resolve_compliance_policy(policy, environment=environment)
    drift = _assess_config_drift(
        base_metrics,
        target_metrics,
        feature_changes,
        policy=effective_policy,
    )

    return {
        "metrics": metric_delta,
        "feature_changes": feature_changes,
        "feature_changes_count": len(feature_changes),
        "drift": drift,
    }


def _assess_config_drift(
    base_metrics: Dict[str, Any],
    target_metrics: Dict[str, Any],
    feature_changes: list[Dict[str, Any]],
    *,
    policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    effective_policy = _resolve_compliance_policy(policy)
    critical_flag_set = set(effective_policy.get("critical_feature_flags", sorted(CRITICAL_FEATURE_FLAGS)))
    suppressions = effective_policy.get("suppressions", [])

    critical_changes = [item for item in feature_changes if str(item.get("feature") or "") in critical_flag_set]
    critical_disabled = [
        item
        for item in critical_changes
        if item.get("before") is True and item.get("after") is False
    ]

    reasons: list[str] = []
    metric_alerts: list[str] = []

    base_incidents = base_metrics.get("incident_count")
    target_incidents = target_metrics.get("incident_count")
    if isinstance(base_incidents, (int, float)) and isinstance(target_incidents, (int, float)):
        if target_incidents - base_incidents >= int(effective_policy.get("incident_spike_delta", 5)):
            metric_alerts.append("incident_count_spike")
            reasons.append("Incidentes aumentaron significativamente entre snapshots")

    base_mtta = base_metrics.get("mtta_minutes")
    target_mtta = target_metrics.get("mtta_minutes")
    if isinstance(base_mtta, (int, float)) and isinstance(target_mtta, (int, float)) and base_mtta > 0:
        if ((target_mtta - base_mtta) / base_mtta) >= float(effective_policy.get("mtta_regression_pct", 0.25)):
            metric_alerts.append("mtta_regression")
            reasons.append("MTTA empeoro mas del 25%")

    base_mttr = base_metrics.get("mttr_minutes")
    target_mttr = target_metrics.get("mttr_minutes")
    if isinstance(base_mttr, (int, float)) and isinstance(target_mttr, (int, float)) and base_mttr > 0:
        if ((target_mttr - base_mttr) / base_mttr) >= float(effective_policy.get("mttr_regression_pct", 0.25)):
            metric_alerts.append("mttr_regression")
            reasons.append("MTTR empeoro mas del 25%")

    severity = "low"
    if critical_disabled and bool(effective_policy.get("critical_feature_disabled_force", True)):
        severity = "critical"
        reasons.append("Se desactivaron flags criticos")
    elif len(critical_changes) >= int(effective_policy.get("critical_feature_change_count_high", 2)):
        severity = "high"
        reasons.append("Multiples flags criticos cambiaron en el periodo")
    elif len(critical_changes) == 1:
        severity = "medium"
        reasons.append("Cambio en un flag critico")
    elif len(feature_changes) >= 3:
        severity = "medium"
        reasons.append("Cambios simultaneos en varios flags")

    if metric_alerts and severity == "low":
        severity = "medium"
    if len(metric_alerts) >= 2 and severity in {"medium", "low"}:
        severity = "high"

    risk_score = 0
    risk_score += min(len(feature_changes) * 8, 30)
    risk_score += min(len(critical_changes) * 15, 30)
    risk_score += min(len(critical_disabled) * 25, 40)
    risk_score += min(len(metric_alerts) * 12, 24)
    risk_score = min(risk_score, 100)

    if severity == "critical":
        risk_score = max(risk_score, 85)
    elif severity == "high":
        risk_score = max(risk_score, 65)
    elif severity == "medium":
        risk_score = max(risk_score, 35)

    mitigations: list[str] = []
    if critical_disabled:
        mitigations.append("Revisar y restaurar flags criticos desactivados sin aprobacion formal")
        mitigations.append("Aplicar control de cambios con doble aprobacion para flags criticos")
    if "incident_count_spike" in metric_alerts:
        mitigations.append("Escanear incidentes inmediatamente y confirmar acciones de contencion")
    if "mtta_regression" in metric_alerts:
        mitigations.append("Reducir MTTA: asignar on-call dedicado y alerta temprana de incidentes")
    if "mttr_regression" in metric_alerts:
        mitigations.append("Reducir MTTR: playbook de remediacion y ownership por dominio")
    if len(feature_changes) >= 3:
        mitigations.append("Separar cambios de flags en lotes pequenos para reducir riesgo acumulado")
    if not mitigations and feature_changes:
        mitigations.append("Registrar RFC de cambio y monitorear impacto por 24h")

    suppressed_feature_changes = [
        item for item in feature_changes if _is_drift_signal_suppressed("feature", str(item.get("feature") or ""), suppressions)
    ]
    active_feature_changes = [item for item in feature_changes if item not in suppressed_feature_changes]

    suppressed_metric_alerts = [
        item for item in metric_alerts if _is_drift_signal_suppressed("metric_alert", item, suppressions)
    ]
    active_metric_alerts = [item for item in metric_alerts if item not in suppressed_metric_alerts]

    suppressed_severity = _is_drift_signal_suppressed("severity", severity, suppressions)

    effective_has_drift = bool(active_feature_changes or active_metric_alerts)
    effective_severity = severity
    if suppressed_severity:
        effective_severity = "low"
        effective_has_drift = False
    elif not effective_has_drift:
        effective_severity = "low"

    return {
        "has_drift": bool(feature_changes or metric_alerts),
        "effective_has_drift": effective_has_drift,
        "severity": severity,
        "effective_severity": effective_severity,
        "risk_score": risk_score,
        "reasons": reasons,
        "mitigations": mitigations,
        "critical_feature_changes": critical_changes,
        "critical_disabled": critical_disabled,
        "non_critical_feature_changes": [item for item in feature_changes if item not in critical_changes],
        "metric_alerts": metric_alerts,
        "suppressions_active": suppressions,
        "suppressed": {
            "severity": suppressed_severity,
            "feature_changes": suppressed_feature_changes,
            "metric_alerts": suppressed_metric_alerts,
        },
        "active": {
            "feature_changes": active_feature_changes,
            "metric_alerts": active_metric_alerts,
        },
        "policy": effective_policy,
    }


def _resolve_compare_pair(
    rows: list[Dict[str, Any]],
    from_snapshot_id: str | None,
    to_snapshot_id: str | None,
) -> tuple[Dict[str, Any], Dict[str, Any]]:
    if from_snapshot_id and to_snapshot_id:
        first = _find_snapshot_history_item(rows, from_snapshot_id)
        second = _find_snapshot_history_item(rows, to_snapshot_id)
        if not first or not second:
            raise HTTPException(status_code=404, detail="One or both snapshots were not found")
        return first, second

    if len(rows) < 2:
        raise HTTPException(status_code=422, detail="Need at least two snapshots in history")
    ordered = sorted(rows, key=lambda item: str(item.get("recorded_at") or ""))
    return ordered[-2], ordered[-1]


def _cleanup_snapshot_history(rows: list[Dict[str, Any]], retain_days: int = 90) -> Dict[str, int]:
    safe_days = max(1, min(retain_days, 3650))
    boundary = datetime.now(tz=timezone.utc).timestamp() - (safe_days * 86400)

    removed = 0
    kept: list[Dict[str, Any]] = []
    for row in rows:
        recorded = _parse_timestamp(row.get("recorded_at"))
        if recorded and recorded.timestamp() < boundary:
            removed += 1
            continue
        kept.append(row)

    rows[:] = kept
    return {"removed": removed, "retained": len(rows), "retain_days": safe_days}


def _maybe_emit_snapshot_drift_alert(
    *,
    previous_entry: Dict[str, Any] | None,
    current_entry: Dict[str, Any],
) -> Dict[str, Any] | None:
    if not previous_entry:
        return None

    previous_snapshot = previous_entry.get("snapshot")
    current_snapshot = current_entry.get("snapshot")
    if not isinstance(previous_snapshot, dict) or not isinstance(current_snapshot, dict):
        return None

    current_policy = (current_snapshot.get("config") or {}).get("compliance_policy")
    current_environment = ((current_snapshot.get("inputs") or {}).get("environment") if isinstance(current_snapshot.get("inputs"), dict) else None)
    diff = _compare_snapshot_payloads(
        previous_snapshot,
        current_snapshot,
        policy=current_policy,
        environment=str(current_environment) if current_environment else None,
    )
    drift = diff.get("drift") or {}
    severity = str(drift.get("effective_severity") or drift.get("severity") or "low")

    if severity in {"high", "critical"}:
        _append_notification(
            {
                "type": "compliance_drift_alert",
                "severity": severity,
                "risk_score": drift.get("risk_score"),
                "from_snapshot_id": previous_entry.get("snapshot_id"),
                "to_snapshot_id": current_entry.get("snapshot_id"),
                "reasons": drift.get("reasons", []),
                "critical_disabled": len(drift.get("critical_disabled", []) or []),
                "critical_feature_changes": len(drift.get("critical_feature_changes", []) or []),
                "suppressed": drift.get("suppressed", {}),
            }
        )

    return {
        "from_snapshot_id": previous_entry.get("snapshot_id"),
        "to_snapshot_id": current_entry.get("snapshot_id"),
        "severity": severity,
        "raw_severity": drift.get("severity"),
        "risk_score": drift.get("risk_score"),
        "has_drift": bool(drift.get("effective_has_drift", drift.get("has_drift"))),
        "reasons": drift.get("reasons", []),
        "mitigations": drift.get("mitigations", []),
        "critical_disabled": len(drift.get("critical_disabled", []) or []),
        "critical_feature_changes": len(drift.get("critical_feature_changes", []) or []),
        "suppressed": drift.get("suppressed", {}),
    }


def _weekly_snapshot_summary(rows: list[Dict[str, Any]], weeks: int = 8) -> list[Dict[str, Any]]:
    safe_weeks = max(1, min(weeks, 104))
    now = datetime.now(tz=timezone.utc)

    buckets: Dict[str, Dict[str, Any]] = {}
    for offset in range(safe_weeks):
        anchor = now - timedelta(weeks=(safe_weeks - 1 - offset))
        iso = anchor.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        buckets[key] = {
            "week": key,
            "snapshots": 0,
            "anomaly_snapshots": 0,
            "critical_incident_peaks": 0,
            "high_drift_alerts": 0,
            "critical_drift_alerts": 0,
            "max_risk_score": 0,
        }

    for row in rows:
        recorded_at = _parse_timestamp(row.get("recorded_at"))
        if not recorded_at:
            continue
        iso = recorded_at.isocalendar()
        key = f"{iso.year}-W{iso.week:02d}"
        if key not in buckets:
            continue

        bucket = buckets[key]
        bucket["snapshots"] += 1
        summary = row.get("summary") or {}
        if bool(summary.get("has_anomaly")):
            bucket["anomaly_snapshots"] += 1
        critical_count = int(summary.get("critical_incidents") or 0)
        if critical_count > bucket["critical_incident_peaks"]:
            bucket["critical_incident_peaks"] = critical_count

        drift = row.get("drift_from_previous") or {}
        drift_severity = str(drift.get("severity") or "low")
        if drift_severity == "high":
            bucket["high_drift_alerts"] += 1
        elif drift_severity == "critical":
            bucket["critical_drift_alerts"] += 1

        risk_score = int(drift.get("risk_score") or 0)
        if risk_score > int(bucket.get("max_risk_score") or 0):
            bucket["max_risk_score"] = risk_score

    return [buckets[key] for key in sorted(buckets.keys())]


def _normalize_compliance_policy_update(payload: Dict[str, Any], current_policy: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Policy payload must be an object")

    next_policy = {
        "active_environment": str(current_policy.get("active_environment") or "production"),
        "environments": dict(current_policy.get("environments") or {}),
        "critical_feature_flags": list(current_policy.get("critical_feature_flags") or sorted(CRITICAL_FEATURE_FLAGS)),
        "suppressions": list(current_policy.get("suppressions") or []),
    }

    if "active_environment" in payload:
        env_name = str(payload.get("active_environment") or "").strip().lower()
        if env_name not in {"development", "staging", "production"}:
            raise HTTPException(status_code=422, detail="active_environment must be development|staging|production")
        next_policy["active_environment"] = env_name

    if "critical_feature_flags" in payload:
        flags = payload.get("critical_feature_flags")
        if not isinstance(flags, list):
            raise HTTPException(status_code=422, detail="critical_feature_flags must be a list")
        cleaned = [str(item).strip() for item in flags if str(item).strip()]
        next_policy["critical_feature_flags"] = sorted(set(cleaned))

    if "environments" in payload:
        env_updates = payload.get("environments")
        if not isinstance(env_updates, dict):
            raise HTTPException(status_code=422, detail="environments must be an object")
        merged_envs: Dict[str, Any] = dict(next_policy.get("environments") or {})
        for env_name, env_values in env_updates.items():
            name = str(env_name).strip().lower()
            if name not in {"development", "staging", "production"}:
                raise HTTPException(status_code=422, detail=f"Invalid environment key: {name}")
            if not isinstance(env_values, dict):
                raise HTTPException(status_code=422, detail=f"Environment '{name}' must be an object")
            base_env = dict(merged_envs.get(name) or {})
            merged = {**base_env, **env_values}
            merged_envs[name] = {
                "incident_spike_delta": max(1, int(merged.get("incident_spike_delta", base_env.get("incident_spike_delta", 5)))),
                "mtta_regression_pct": max(0.01, float(merged.get("mtta_regression_pct", base_env.get("mtta_regression_pct", 0.25)))),
                "mttr_regression_pct": max(0.01, float(merged.get("mttr_regression_pct", base_env.get("mttr_regression_pct", 0.25)))),
                "critical_feature_change_count_high": max(1, int(merged.get("critical_feature_change_count_high", base_env.get("critical_feature_change_count_high", 2)))),
                "critical_feature_disabled_force": bool(merged.get("critical_feature_disabled_force", base_env.get("critical_feature_disabled_force", True))),
            }
        next_policy["environments"] = merged_envs

    return next_policy


def _normalize_suppression_payload(payload: Dict[str, Any], actor_id: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Suppression payload must be an object")

    kind = str(payload.get("kind") or "").strip().lower()
    value = str(payload.get("value") or "").strip().lower()
    note = str(payload.get("note") or "").strip()
    expires_in_hours_raw = payload.get("expires_in_hours", 24)

    if kind not in {"all", "severity", "feature", "metric_alert"}:
        raise HTTPException(status_code=422, detail="kind must be all|severity|feature|metric_alert")
    if kind != "all" and not value:
        raise HTTPException(status_code=422, detail="value is required for this suppression kind")

    try:
        expires_in_hours = max(1, min(int(expires_in_hours_raw), 24 * 30))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="expires_in_hours must be an integer")

    now = datetime.now(tz=timezone.utc)
    expires_at = (now + timedelta(hours=expires_in_hours)).isoformat()
    suppression_id = hashlib.md5(f"{kind}:{value}:{now.isoformat()}:{actor_id}".encode("utf-8")).hexdigest()[:12]

    return {
        "id": suppression_id,
        "kind": kind,
        "value": value,
        "note": note,
        "created_by": actor_id,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
    }


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


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


def _load_incidents() -> list[Dict[str, Any]]:
    if not INCIDENTS_FILE.exists():
        return []
    try:
        payload = json.loads(INCIDENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
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
                "history": item.get("history") if isinstance(item.get("history"), list) else [],
            }
        )
    return normalized


def _save_incidents(incidents: list[Dict[str, Any]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    INCIDENTS_FILE.write_text(json.dumps(incidents, ensure_ascii=True, indent=2), encoding="utf-8")


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


def _incident_daily_trends(incidents: list[Dict[str, Any]], days: int = 14) -> list[Dict[str, Any]]:
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
            mttr_seconds = _seconds_between(incident.get("created_at"), incident.get("closed_at"))
            if mttr_seconds is not None:
                buckets[closed_key]["mttr_values"].append(mttr_seconds / 60.0)

        ack_key = _day_key(incident.get("ack_at"))
        if ack_key in buckets:
            buckets[ack_key]["acknowledged"] += 1
            mtta_seconds = _seconds_between(incident.get("created_at"), incident.get("ack_at"))
            if mtta_seconds is not None:
                buckets[ack_key]["mtta_values"].append(mtta_seconds / 60.0)

    rows: list[Dict[str, Any]] = []
    for day in sorted(buckets.keys()):
        row = buckets[day]
        mtta_values = row.pop("mtta_values")
        mttr_values = row.pop("mttr_values")
        row["mtta_avg_minutes"] = round(sum(mtta_values) / len(mtta_values), 2) if mtta_values else None
        row["mttr_avg_minutes"] = round(sum(mttr_values) / len(mttr_values), 2) if mttr_values else None
        rows.append(row)

    return rows


def _period_bounds(window: str = "weekly") -> tuple[datetime, datetime, datetime, datetime, int]:
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


def _period_incident_stats(incidents: list[Dict[str, Any]], start: datetime, end: datetime) -> Dict[str, Any]:
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
            close_seconds = _seconds_between(item.get("created_at"), item.get("closed_at"))
            if close_seconds is not None:
                mttr_values.append(close_seconds / 60.0)

        is_active_at_end = created_at is not None and created_at < end and (closed_at is None or closed_at >= end)
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


def _pct_delta(current: float | int | None, previous: float | int | None) -> float | None:
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
        existing = next((item for item in incidents if item.get("fingerprint") == fingerprint and item.get("status") != "closed"), None)

        if existing:
            previous_count = int(existing.get("count") or 0)
            existing["count"] = candidate["count"]
            existing["threshold"] = candidate["threshold"]
            existing["updated_at"] = now
            existing["last_seen_at"] = now
            if existing.get("status") == "silenced" and not _is_silenced_active(existing):
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
                "id": hashlib.md5(f"{fingerprint}:{now}".encode("utf-8")).hexdigest()[:12],
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
        _set_incident_severity(incidents[-1], actor_id="system", reason="created_by_scan")
        created += 1

    return {
        "created": created,
        "updated": updated,
        "total_candidates": len(candidates),
    }


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
        filtered = [row for row in filtered if str(row.get("action", "")).lower() == action_norm]
    if feature_id:
        filtered = [row for row in filtered if str(row.get("feature_id", "")) == feature_id]
    if actor:
        actor_norm = actor.strip()
        filtered = [row for row in filtered if str(row.get("updated_by", "")) == actor_norm]
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
    top_features = sorted(by_feature.items(), key=lambda item: item[1], reverse=True)[:5]

    return {
        "total_events": len(rows),
        "by_action": by_action,
        "top_actors": [{"actor": actor, "count": count} for actor, count in top_actors],
        "top_features": [{"feature": feature, "count": count} for feature, count in top_features],
    }


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
        for actor, count in sorted(by_actor.items(), key=lambda item: item[1], reverse=True)
        if count >= safe_actor_threshold
    ]
    action_spikes = [
        {"action": action, "count": count, "threshold": safe_action_threshold}
        for action, count in sorted(by_action.items(), key=lambda item: item[1], reverse=True)
        if count >= safe_action_threshold
    ]

    return {
        "lookback_hours": safe_hours,
        "recent_events": len(recent),
        "has_anomaly": bool(actor_spikes or action_spikes),
        "actor_spikes": actor_spikes,
        "action_spikes": action_spikes,
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


@router.get("/config")
def get_workspace_config(current_user: models.User = Depends(require_active_user)):
    config = _load_workspace_config()
    config["features_raw"] = config.get("features_enabled", {}).copy()
    config["features_enabled"] = _resolve_features(config, current_user)
    config["requested_by"] = str(getattr(current_user, "id", ""))
    return config


@router.put("/flags", dependencies=[Depends(rate_limiter(limit=20, window_seconds=60))])
def update_feature_flags(
    payload: Dict[str, bool],
    current_user: models.User = Depends(require_admin),
):
    config = _load_workspace_config()
    current = config.get("features_enabled", {})
    known_features = set((config.get("features_enabled") or {}).keys()) | set((DEFAULT_WORKSPACE_CONFIG.get("features_enabled") or {}).keys())
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


@router.put("/flags/rules/{feature_id}", dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))])
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


@router.get("/flags/incidents", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
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
        incidents = [item for item in incidents if str(item.get("status", "")).lower() == status_norm]

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


@router.get("/flags/incidents/summary", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
def get_flags_incidents_summary(
    status: str | None = None,
    mtta_target_minutes: int = 60,
    mttr_target_minutes: int = 240,
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    if status:
        status_norm = status.strip().lower()
        incidents = [item for item in incidents if str(item.get("status", "")).lower() == status_norm]
    return {
        "status": "ok",
        "requested_by": str(getattr(current_user, "id", "")),
        "summary": _summarize_incidents(
            incidents,
            mtta_target_minutes=mtta_target_minutes,
            mttr_target_minutes=mttr_target_minutes,
        ),
    }


@router.get("/flags/incidents/trends", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
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


@router.get("/flags/incidents/notifications", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
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


@router.get("/flags/incidents/stats", dependencies=[Depends(rate_limiter(limit=60, window_seconds=60))])
def get_flags_incidents_stats(
    window: str = "weekly",
    current_user: models.User = Depends(require_admin),
):
    incidents = _load_incidents()
    current_start, current_end, previous_start, previous_end, days = _period_bounds(window)

    current_stats = _period_incident_stats(incidents, current_start, current_end)
    previous_stats = _period_incident_stats(incidents, previous_start, previous_end)

    deltas = {
        "created_pct": _pct_delta(current_stats.get("created"), previous_stats.get("created")),
        "closed_pct": _pct_delta(current_stats.get("closed"), previous_stats.get("closed")),
        "closure_rate_pct": _pct_delta(current_stats.get("closure_rate"), previous_stats.get("closure_rate")),
        "mtta_pct": _pct_delta(current_stats.get("mtta_minutes"), previous_stats.get("mtta_minutes")),
        "mttr_pct": _pct_delta(current_stats.get("mttr_minutes"), previous_stats.get("mttr_minutes")),
        "active_end_pct": _pct_delta(current_stats.get("active_end"), previous_stats.get("active_end")),
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


@router.get("/flags/incidents/export", dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))])
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
        incidents = [item for item in incidents if str(item.get("status", "")).lower() == status_norm]
    if severity:
        severity_norm = severity.strip().lower()
        incidents = [item for item in incidents if str(item.get("severity", "")).lower() == severity_norm]

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
            headers={"Content-Disposition": "attachment; filename=feature_flags_incidents.json"},
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
            headers={"Content-Disposition": "attachment; filename=feature_flags_incidents.csv"},
        )

    raise HTTPException(status_code=400, detail="format must be 'json' or 'csv'")


def _build_compliance_snapshot(
    *,
    actor_id: str,
    environment: str | None = None,
    audit_limit: int = 200,
    incident_limit: int = 200,
    lookback_hours: int = 24,
    actor_threshold: int = 10,
    action_threshold: int = 20,
) -> Dict[str, Any]:
    config = _load_workspace_config()
    policy = _resolve_compliance_policy(config.get("compliance_policy"), environment=environment)
    audit_rows = _enrich_audit_rows(_read_audit_events(limit=max(1, min(audit_limit, 1000))))
    incidents = _load_incidents()
    incidents = incidents[-max(1, min(incident_limit, 1000)) :]

    anomalies = _detect_anomalies(
        audit_rows,
        lookback_hours=lookback_hours,
        actor_threshold=actor_threshold,
        action_threshold=action_threshold,
    )

    weekly_start, weekly_end, weekly_prev_start, weekly_prev_end, _ = _period_bounds("weekly")
    monthly_start, monthly_end, monthly_prev_start, monthly_prev_end, _ = _period_bounds("monthly")

    weekly_current = _period_incident_stats(incidents, weekly_start, weekly_end)
    weekly_previous = _period_incident_stats(incidents, weekly_prev_start, weekly_prev_end)
    monthly_current = _period_incident_stats(incidents, monthly_start, monthly_end)
    monthly_previous = _period_incident_stats(incidents, monthly_prev_start, monthly_prev_end)

    snapshot = {
        "schema_version": COMPLIANCE_SNAPSHOT_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "requested_by": actor_id,
        "inputs": {
            "environment": policy.get("environment"),
            "audit_limit": max(1, min(audit_limit, 1000)),
            "incident_limit": max(1, min(incident_limit, 1000)),
            "lookback_hours": max(1, min(lookback_hours, 720)),
            "actor_threshold": max(2, min(actor_threshold, 1000)),
            "action_threshold": max(2, min(action_threshold, 5000)),
        },
        "config": {
            "features_enabled": config.get("features_enabled", {}),
            "feature_rules": config.get("feature_rules", {}),
            "compliance_policy": {
                "active_environment": policy.get("environment"),
                "critical_feature_flags": policy.get("critical_feature_flags", []),
            },
        },
        "audit": {
            "count": len(audit_rows),
            "summary": _summarize_audit(audit_rows),
            "anomalies": anomalies,
            "latest_events": audit_rows[-20:],
        },
        "incidents": {
            "count": len(incidents),
            "summary": _summarize_incidents(incidents),
            "notifications": _read_notifications(limit=50),
            "latest": incidents[-20:],
            "trends_14d": _incident_daily_trends(incidents, days=14),
            "stats": {
                "weekly": {
                    "current": weekly_current,
                    "previous": weekly_previous,
                    "deltas": {
                        "created_pct": _pct_delta(weekly_current.get("created"), weekly_previous.get("created")),
                        "closed_pct": _pct_delta(weekly_current.get("closed"), weekly_previous.get("closed")),
                        "mtta_pct": _pct_delta(weekly_current.get("mtta_minutes"), weekly_previous.get("mtta_minutes")),
                        "mttr_pct": _pct_delta(weekly_current.get("mttr_minutes"), weekly_previous.get("mttr_minutes")),
                    },
                },
                "monthly": {
                    "current": monthly_current,
                    "previous": monthly_previous,
                    "deltas": {
                        "created_pct": _pct_delta(monthly_current.get("created"), monthly_previous.get("created")),
                        "closed_pct": _pct_delta(monthly_current.get("closed"), monthly_previous.get("closed")),
                        "mtta_pct": _pct_delta(monthly_current.get("mtta_minutes"), monthly_previous.get("mtta_minutes")),
                        "mttr_pct": _pct_delta(monthly_current.get("mttr_minutes"), monthly_previous.get("mttr_minutes")),
                    },
                },
            },
        },
    }
    payload_hash = _snapshot_hash(snapshot)
    snapshot_id = payload_hash[:16]
    snapshot["signature"] = {
        "algorithm": "sha256",
        "hash": payload_hash,
        "snapshot_id": snapshot_id,
    }
    return snapshot


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


@router.post("/flags/incidents/scan", dependencies=[Depends(rate_limiter(limit=30, window_seconds=60))])
def scan_flags_incidents(
    lookback_hours: int = 24,
    actor_threshold: int = 10,
    action_threshold: int = 20,
    action: str | None = None,
    feature_id: str | None = None,
    actor: str | None = None,
    current_user: models.User = Depends(require_admin),
):
    rows = _filter_audit_rows(_read_audit_events(limit=1000), action=action, feature_id=feature_id, actor=actor, limit=1000)
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


@router.patch("/flags/incidents/{incident_id}", dependencies=[Depends(rate_limiter(limit=40, window_seconds=60))])
def update_flags_incident(
    incident_id: str,
    payload: Dict[str, Any],
    current_user: models.User = Depends(require_admin),
):
    action = str(payload.get("action") or "").strip().lower()
    note = str(payload.get("note") or "").strip()
    silence_minutes = payload.get("silence_minutes", 60)

    if action not in {"acknowledge", "close", "reopen", "silence", "note"}:
        raise HTTPException(status_code=400, detail="action must be acknowledge|close|reopen|silence|note")

    incidents = _load_incidents()
    incident = next((item for item in incidents if str(item.get("id", "")) == incident_id), None)
    if not incident:
        raise HTTPException(status_code=404, detail="incident not found")

    now = _now_iso()
    actor_id = str(getattr(current_user, "id", ""))

    if action == "acknowledge":
        incident["status"] = "acknowledged"
        incident["ack_by"] = actor_id
        incident["ack_at"] = now
        _append_incident_history(incident, event="acknowledged", actor_id=actor_id, note=note)
    elif action == "close":
        incident["status"] = "closed"
        incident["closed_by"] = actor_id
        incident["closed_at"] = now
        _append_incident_history(incident, event="closed", actor_id=actor_id, note=note)
    elif action == "reopen":
        incident["status"] = "open"
        incident["silenced_until"] = None
        _append_incident_history(incident, event="reopened", actor_id=actor_id, note=note)
    elif action == "silence":
        try:
            minutes = max(1, min(int(silence_minutes), 60 * 24 * 7))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="silence_minutes must be an integer")
        until_dt = datetime.now(tz=timezone.utc).timestamp() + (minutes * 60)
        incident["status"] = "silenced"
        incident["silenced_until"] = datetime.fromtimestamp(until_dt, tz=timezone.utc).isoformat()
        _append_incident_history(
            incident,
            event="silenced",
            actor_id=actor_id,
            note=note,
            metadata={"silence_minutes": minutes},
        )
    elif action == "note":
        if not note:
            raise HTTPException(status_code=422, detail="note is required when action=note")
        _append_incident_history(incident, event="note", actor_id=actor_id, note=note)

    if note:
        incident["note"] = note
    _set_incident_severity(incident, actor_id=actor_id, reason=f"incident_action:{action}")
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


@router.post("/flags/incidents/cleanup", dependencies=[Depends(rate_limiter(limit=10, window_seconds=60))])
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

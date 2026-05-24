from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
FLAGS_FILE = DATA_DIR / "feature_flags.json"
AUDIT_FILE = DATA_DIR / "feature_flags_audit.ndjson"
INCIDENTS_FILE = DATA_DIR / "feature_flags_incidents.json"
NOTIFICATIONS_FILE = DATA_DIR / "feature_flags_notifications.ndjson"
SNAPSHOT_HISTORY_FILE = DATA_DIR / "feature_flags_snapshot_history.ndjson"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_LIST_ITEMS = 200
MAX_USER_REF_LENGTH = 120
ALLOWED_RULE_KEYS = {
    "roles_allow",
    "roles_deny",
    "users_allow",
    "users_deny",
    "rollout_percent",
}
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

DEFAULT_WORKSPACE_CONFIG["compliance_policy"] = DEFAULT_COMPLIANCE_POLICY

# ---------------------------------------------------------------------------
# Re-export all functions from submodules
# ---------------------------------------------------------------------------

# _audit
from backend.api.workspace_shared._audit import (_build_event_diff,
                                                 _enrich_audit_rows,
                                                 _filter_audit_rows,
                                                 _parse_timestamp,
                                                 _summarize_audit)
# _flags
from backend.api.workspace_shared._flags import (_normalize_role_list,
                                                 _normalize_rollout,
                                                 _normalize_rule_payload,
                                                 _normalize_user_list,
                                                 _resolve_features,
                                                 _sanitize_feature_payload,
                                                 _stable_rollout_hit)
# _incidents
from backend.api.workspace_shared._incidents import (
    _cleanup_incidents, _compute_incident_severity, _detect_anomalies,
    _in_range, _incident_daily_trends, _incident_fingerprint,
    _is_silenced_active, _pct_delta, _period_bounds, _period_incident_stats,
    _scan_incidents_from_anomalies, _seconds_between, _set_incident_severity,
    _summarize_incidents)
# _snapshots
from backend.api.workspace_shared._snapshots import (
    _assess_config_drift, _build_compliance_snapshot,
    _cleanup_snapshot_history, _compare_snapshot_payloads,
    _find_snapshot_history_item, _is_drift_signal_suppressed,
    _maybe_emit_snapshot_drift_alert, _normalize_compliance_policy_update,
    _normalize_suppression_payload, _resolve_compare_pair,
    _resolve_compliance_policy, _snapshot_hash, _snapshot_metrics,
    _verify_snapshot_history_item, _weekly_snapshot_summary)
# _storage
from backend.api.workspace_shared._storage import (_append_audit_event,
                                                   _append_incident_history,
                                                   _append_notification,
                                                   _append_snapshot_history,
                                                   _json_canonical,
                                                   _load_incidents,
                                                   _load_workspace_config,
                                                   _now_iso,
                                                   _read_audit_events,
                                                   _read_notifications,
                                                   _read_snapshot_history,
                                                   _save_incidents,
                                                   _save_snapshot_history,
                                                   _save_workspace_config)

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import HTTPException

from backend.api.workspace_shared import (COMPLIANCE_SNAPSHOT_SCHEMA_VERSION,
                                          CRITICAL_FEATURE_FLAGS,
                                          DEFAULT_COMPLIANCE_POLICY)
from backend.api.workspace_shared._audit import (_enrich_audit_rows,
                                                 _parse_timestamp,
                                                 _summarize_audit)
from backend.api.workspace_shared._incidents import (
    _detect_anomalies, _incident_daily_trends, _pct_delta, _period_bounds,
    _period_incident_stats, _scan_incidents_from_anomalies,
    _summarize_incidents)
from backend.api.workspace_shared._storage import (_append_notification,
                                                   _append_snapshot_history,
                                                   _json_canonical,
                                                   _load_incidents,
                                                   _load_workspace_config,
                                                   _now_iso,
                                                   _read_audit_events,
                                                   _read_notifications,
                                                   _read_snapshot_history,
                                                   _save_snapshot_history,
                                                   _save_workspace_config)


def _snapshot_hash(snapshot: Dict[str, Any]) -> str:
    return hashlib.sha256(_json_canonical(snapshot).encode("utf-8")).hexdigest()


def _find_snapshot_history_item(
    rows: list[Dict[str, Any]], snapshot_id: str
) -> Dict[str, Any] | None:
    return next(
        (
            row
            for row in reversed(rows)
            if str(row.get("snapshot_id", "")) == snapshot_id
        ),
        None,
    )


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
    env_name = (
        (environment or source.get("active_environment") or "production")
        .strip()
        .lower()
    )
    envs = (
        source.get("environments")
        if isinstance(source.get("environments"), dict)
        else {}
    )
    env_policy = envs.get(env_name) if isinstance(envs.get(env_name), dict) else {}
    if not env_policy and env_name != "production":
        env_policy = (
            envs.get("production") if isinstance(envs.get("production"), dict) else {}
        )

    suppressions_raw = (
        source.get("suppressions")
        if isinstance(source.get("suppressions"), list)
        else []
    )
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
        for flag in (
            critical_flags
            if isinstance(critical_flags, list)
            else sorted(CRITICAL_FEATURE_FLAGS)
        )
        if str(flag).strip()
    }
    if not critical_flag_set:
        critical_flag_set = set(CRITICAL_FEATURE_FLAGS)

    return {
        "environment": env_name,
        "incident_spike_delta": max(1, int(env_policy.get("incident_spike_delta", 5))),
        "mtta_regression_pct": max(
            0.01, float(env_policy.get("mtta_regression_pct", 0.25))
        ),
        "mttr_regression_pct": max(
            0.01, float(env_policy.get("mttr_regression_pct", 0.25))
        ),
        "critical_feature_change_count_high": max(
            1, int(env_policy.get("critical_feature_change_count_high", 2))
        ),
        "critical_feature_disabled_force": bool(
            env_policy.get("critical_feature_disabled_force", True)
        ),
        "critical_feature_flags": sorted(critical_flag_set),
        "suppressions": suppressions,
    }


def _is_drift_signal_suppressed(
    signal_type: str, signal_value: str, suppressions: list[Dict[str, Any]]
) -> bool:
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
    critical_flag_set = set(
        effective_policy.get("critical_feature_flags", sorted(CRITICAL_FEATURE_FLAGS))
    )
    suppressions = effective_policy.get("suppressions", [])

    critical_changes = [
        item
        for item in feature_changes
        if str(item.get("feature") or "") in critical_flag_set
    ]
    critical_disabled = [
        item
        for item in critical_changes
        if item.get("before") is True and item.get("after") is False
    ]

    reasons: list[str] = []
    metric_alerts: list[str] = []

    base_incidents = base_metrics.get("incident_count")
    target_incidents = target_metrics.get("incident_count")
    if isinstance(base_incidents, (int, float)) and isinstance(
        target_incidents, (int, float)
    ):
        if target_incidents - base_incidents >= int(
            effective_policy.get("incident_spike_delta", 5)
        ):
            metric_alerts.append("incident_count_spike")
            reasons.append("Incidentes aumentaron significativamente entre snapshots")

    base_mtta = base_metrics.get("mtta_minutes")
    target_mtta = target_metrics.get("mtta_minutes")
    if (
        isinstance(base_mtta, (int, float))
        and isinstance(target_mtta, (int, float))
        and base_mtta > 0
    ):
        if ((target_mtta - base_mtta) / base_mtta) >= float(
            effective_policy.get("mtta_regression_pct", 0.25)
        ):
            metric_alerts.append("mtta_regression")
            reasons.append("MTTA empeoro mas del 25%")

    base_mttr = base_metrics.get("mttr_minutes")
    target_mttr = target_metrics.get("mttr_minutes")
    if (
        isinstance(base_mttr, (int, float))
        and isinstance(target_mttr, (int, float))
        and base_mttr > 0
    ):
        if ((target_mttr - base_mttr) / base_mttr) >= float(
            effective_policy.get("mttr_regression_pct", 0.25)
        ):
            metric_alerts.append("mttr_regression")
            reasons.append("MTTR empeoro mas del 25%")

    severity = "low"
    if critical_disabled and bool(
        effective_policy.get("critical_feature_disabled_force", True)
    ):
        severity = "critical"
        reasons.append("Se desactivaron flags criticos")
    elif len(critical_changes) >= int(
        effective_policy.get("critical_feature_change_count_high", 2)
    ):
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
        mitigations.append(
            "Revisar y restaurar flags criticos desactivados sin aprobacion formal"
        )
        mitigations.append(
            "Aplicar control de cambios con doble aprobacion para flags criticos"
        )
    if "incident_count_spike" in metric_alerts:
        mitigations.append(
            "Escanear incidentes inmediatamente y confirmar acciones de contencion"
        )
    if "mtta_regression" in metric_alerts:
        mitigations.append(
            "Reducir MTTA: asignar on-call dedicado y alerta temprana de incidentes"
        )
    if "mttr_regression" in metric_alerts:
        mitigations.append(
            "Reducir MTTR: playbook de remediacion y ownership por dominio"
        )
    if len(feature_changes) >= 3:
        mitigations.append(
            "Separar cambios de flags en lotes pequenos para reducir riesgo acumulado"
        )
    if not mitigations and feature_changes:
        mitigations.append("Registrar RFC de cambio y monitorear impacto por 24h")

    suppressed_feature_changes = [
        item
        for item in feature_changes
        if _is_drift_signal_suppressed(
            "feature", str(item.get("feature") or ""), suppressions
        )
    ]
    active_feature_changes = [
        item for item in feature_changes if item not in suppressed_feature_changes
    ]

    suppressed_metric_alerts = [
        item
        for item in metric_alerts
        if _is_drift_signal_suppressed("metric_alert", item, suppressions)
    ]
    active_metric_alerts = [
        item for item in metric_alerts if item not in suppressed_metric_alerts
    ]

    suppressed_severity = _is_drift_signal_suppressed(
        "severity", severity, suppressions
    )

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
        "non_critical_feature_changes": [
            item for item in feature_changes if item not in critical_changes
        ],
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
            raise HTTPException(
                status_code=404, detail="One or both snapshots were not found"
            )
        return first, second

    if len(rows) < 2:
        raise HTTPException(
            status_code=422, detail="Need at least two snapshots in history"
        )
    ordered = sorted(rows, key=lambda item: str(item.get("recorded_at") or ""))
    return ordered[-2], ordered[-1]


def _cleanup_snapshot_history(
    rows: list[Dict[str, Any]], retain_days: int = 90
) -> Dict[str, int]:
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
    if not isinstance(previous_snapshot, dict) or not isinstance(
        current_snapshot, dict
    ):
        return None

    current_policy = (current_snapshot.get("config") or {}).get("compliance_policy")
    current_environment = (
        (current_snapshot.get("inputs") or {}).get("environment")
        if isinstance(current_snapshot.get("inputs"), dict)
        else None
    )
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
                "critical_feature_changes": len(
                    drift.get("critical_feature_changes", []) or []
                ),
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
        "critical_feature_changes": len(
            drift.get("critical_feature_changes", []) or []
        ),
        "suppressed": drift.get("suppressed", {}),
    }


def _weekly_snapshot_summary(
    rows: list[Dict[str, Any]], weeks: int = 8
) -> list[Dict[str, Any]]:
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


def _normalize_compliance_policy_update(
    payload: Dict[str, Any], current_policy: Dict[str, Any]
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Policy payload must be an object")

    next_policy = {
        "active_environment": str(
            current_policy.get("active_environment") or "production"
        ),
        "environments": dict(current_policy.get("environments") or {}),
        "critical_feature_flags": list(
            current_policy.get("critical_feature_flags")
            or sorted(CRITICAL_FEATURE_FLAGS)
        ),
        "suppressions": list(current_policy.get("suppressions") or []),
    }

    if "active_environment" in payload:
        env_name = str(payload.get("active_environment") or "").strip().lower()
        if env_name not in {"development", "staging", "production"}:
            raise HTTPException(
                status_code=422,
                detail="active_environment must be development|staging|production",
            )
        next_policy["active_environment"] = env_name

    if "critical_feature_flags" in payload:
        flags = payload.get("critical_feature_flags")
        if not isinstance(flags, list):
            raise HTTPException(
                status_code=422, detail="critical_feature_flags must be a list"
            )
        cleaned = [str(item).strip() for item in flags if str(item).strip()]
        next_policy["critical_feature_flags"] = sorted(set(cleaned))

    if "environments" in payload:
        env_updates = payload.get("environments")
        if not isinstance(env_updates, dict):
            raise HTTPException(
                status_code=422, detail="environments must be an object"
            )
        merged_envs: Dict[str, Any] = dict(next_policy.get("environments") or {})
        for env_name, env_values in env_updates.items():
            name = str(env_name).strip().lower()
            if name not in {"development", "staging", "production"}:
                raise HTTPException(
                    status_code=422, detail=f"Invalid environment key: {name}"
                )
            if not isinstance(env_values, dict):
                raise HTTPException(
                    status_code=422, detail=f"Environment '{name}' must be an object"
                )
            base_env = dict(merged_envs.get(name) or {})
            merged = {**base_env, **env_values}
            merged_envs[name] = {
                "incident_spike_delta": max(
                    1,
                    int(
                        merged.get(
                            "incident_spike_delta",
                            base_env.get("incident_spike_delta", 5),
                        )
                    ),
                ),
                "mtta_regression_pct": max(
                    0.01,
                    float(
                        merged.get(
                            "mtta_regression_pct",
                            base_env.get("mtta_regression_pct", 0.25),
                        )
                    ),
                ),
                "mttr_regression_pct": max(
                    0.01,
                    float(
                        merged.get(
                            "mttr_regression_pct",
                            base_env.get("mttr_regression_pct", 0.25),
                        )
                    ),
                ),
                "critical_feature_change_count_high": max(
                    1,
                    int(
                        merged.get(
                            "critical_feature_change_count_high",
                            base_env.get("critical_feature_change_count_high", 2),
                        )
                    ),
                ),
                "critical_feature_disabled_force": bool(
                    merged.get(
                        "critical_feature_disabled_force",
                        base_env.get("critical_feature_disabled_force", True),
                    )
                ),
            }
        next_policy["environments"] = merged_envs

    return next_policy


def _normalize_suppression_payload(
    payload: Dict[str, Any], actor_id: str
) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=422, detail="Suppression payload must be an object"
        )

    kind = str(payload.get("kind") or "").strip().lower()
    value = str(payload.get("value") or "").strip().lower()
    note = str(payload.get("note") or "").strip()
    expires_in_hours_raw = payload.get("expires_in_hours", 24)

    if kind not in {"all", "severity", "feature", "metric_alert"}:
        raise HTTPException(
            status_code=422, detail="kind must be all|severity|feature|metric_alert"
        )
    if kind != "all" and not value:
        raise HTTPException(
            status_code=422, detail="value is required for this suppression kind"
        )

    try:
        expires_in_hours = max(1, min(int(expires_in_hours_raw), 24 * 30))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422, detail="expires_in_hours must be an integer"
        )

    now = datetime.now(tz=timezone.utc)
    expires_at = (now + timedelta(hours=expires_in_hours)).isoformat()
    suppression_id = hashlib.md5(
        f"{kind}:{value}:{now.isoformat()}:{actor_id}".encode("utf-8")
    ).hexdigest()[:12]

    return {
        "id": suppression_id,
        "kind": kind,
        "value": value,
        "note": note,
        "created_by": actor_id,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
    }


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
    policy = _resolve_compliance_policy(
        config.get("compliance_policy"), environment=environment
    )
    audit_rows = _enrich_audit_rows(
        _read_audit_events(limit=max(1, min(audit_limit, 1000)))
    )
    incidents = _load_incidents()
    incidents = incidents[-max(1, min(incident_limit, 1000)) :]

    anomalies = _detect_anomalies(
        audit_rows,
        lookback_hours=lookback_hours,
        actor_threshold=actor_threshold,
        action_threshold=action_threshold,
    )

    weekly_start, weekly_end, weekly_prev_start, weekly_prev_end, _ = _period_bounds(
        "weekly"
    )
    monthly_start, monthly_end, monthly_prev_start, monthly_prev_end, _ = (
        _period_bounds("monthly")
    )

    weekly_current = _period_incident_stats(incidents, weekly_start, weekly_end)
    weekly_previous = _period_incident_stats(
        incidents, weekly_prev_start, weekly_prev_end
    )
    monthly_current = _period_incident_stats(incidents, monthly_start, monthly_end)
    monthly_previous = _period_incident_stats(
        incidents, monthly_prev_start, monthly_prev_end
    )

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
                        "created_pct": _pct_delta(
                            weekly_current.get("created"),
                            weekly_previous.get("created"),
                        ),
                        "closed_pct": _pct_delta(
                            weekly_current.get("closed"), weekly_previous.get("closed")
                        ),
                        "mtta_pct": _pct_delta(
                            weekly_current.get("mtta_minutes"),
                            weekly_previous.get("mtta_minutes"),
                        ),
                        "mttr_pct": _pct_delta(
                            weekly_current.get("mttr_minutes"),
                            weekly_previous.get("mttr_minutes"),
                        ),
                    },
                },
                "monthly": {
                    "current": monthly_current,
                    "previous": monthly_previous,
                    "deltas": {
                        "created_pct": _pct_delta(
                            monthly_current.get("created"),
                            monthly_previous.get("created"),
                        ),
                        "closed_pct": _pct_delta(
                            monthly_current.get("closed"),
                            monthly_previous.get("closed"),
                        ),
                        "mtta_pct": _pct_delta(
                            monthly_current.get("mtta_minutes"),
                            monthly_previous.get("mtta_minutes"),
                        ),
                        "mttr_pct": _pct_delta(
                            monthly_current.get("mttr_minutes"),
                            monthly_previous.get("mttr_minutes"),
                        ),
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

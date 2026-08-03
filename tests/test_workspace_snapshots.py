"""Tests for _snapshots.py — pure dict/list logic, no DB."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from backend.api.workspace_shared._snapshots import (
    _assess_config_drift,
    _cleanup_snapshot_history,
    _compare_snapshot_payloads,
    _find_snapshot_history_item,
    _is_drift_signal_suppressed,
    _maybe_emit_snapshot_drift_alert,
    _normalize_compliance_policy_update,
    _normalize_suppression_payload,
    _resolve_compare_pair,
    _resolve_compliance_policy,
    _snapshot_hash,
    _snapshot_metrics,
    _verify_snapshot_history_item,
    _weekly_snapshot_summary,
)

# ── _snapshot_hash ─────────────────────────────────────────────────────────────

class TestSnapshotHash:
    def test_consistency(self):
        snap = {"a": 1, "b": [2, 3]}
        assert _snapshot_hash(snap) == _snapshot_hash(snap)

    def test_changes_with_content(self):
        assert _snapshot_hash({"a": 1}) != _snapshot_hash({"a": 2})


# ── _find_snapshot_history_item ────────────────────────────────────────────────

class TestFindSnapshotHistoryItem:
    def test_finds_by_id(self):
        rows = [{"snapshot_id": "a"}, {"snapshot_id": "b"}, {"snapshot_id": "c"}]
        assert _find_snapshot_history_item(rows, "b")["snapshot_id"] == "b"

    def test_not_found(self):
        assert _find_snapshot_history_item([], "x") is None

    def test_searches_reversed(self):
        rows = [{"snapshot_id": "a"}, {"snapshot_id": "b"}]
        assert _find_snapshot_history_item(rows, "a")["snapshot_id"] == "a"


# ── _verify_snapshot_history_item ──────────────────────────────────────────────

class TestVerifySnapshotHistoryItem:
    def test_valid(self):
        snap = {"x": 1}
        item = {"snapshot": snap, "signature": {"hash": _snapshot_hash(snap)}}
        result = _verify_snapshot_history_item(item)
        assert result["ok"] is True

    def test_invalid_hash(self):
        item = {"snapshot": {"x": 1}, "signature": {"hash": "bad"}}
        assert _verify_snapshot_history_item(item)["ok"] is False

    def test_missing_snapshot(self):
        result = _verify_snapshot_history_item({"signature": {"hash": "x"}})
        assert result["ok"] is False
        assert result["reason"] == "missing_snapshot_payload"

    def test_no_signature(self):
        result = _verify_snapshot_history_item({"snapshot": {}})
        assert result["ok"] is False

    def test_empty_signature_hash(self):
        item = {"snapshot": {"x": 1}, "signature": {"hash": ""}}
        assert _verify_snapshot_history_item(item)["ok"] is False


# ── _snapshot_metrics ──────────────────────────────────────────────────────────

class TestSnapshotMetrics:
    def test_all_fields(self):
        snap = {
            "audit": {"count": 42, "anomalies": {"has_anomaly": True}},
            "incidents": {
                "count": 10,
                "summary": {
                    "severity_counts": {"critical": 2, "high": 3},
                    "mtta_minutes": 30, "mttr_minutes": 120,
                },
            },
        }
        m = _snapshot_metrics(snap)
        assert m == {
            "audit_count": 42, "has_anomaly": True, "incident_count": 10,
            "critical_incidents": 2, "high_incidents": 3,
            "mtta_minutes": 30, "mttr_minutes": 120,
        }

    def test_empty(self):
        m = _snapshot_metrics({})
        assert m["audit_count"] is None
        assert m["mtta_minutes"] is None


# ── _resolve_compliance_policy ─────────────────────────────────────────────────

class TestResolveCompliancePolicy:
    def test_default(self):
        r = _resolve_compliance_policy()
        assert r["environment"] == "production"
        assert r["incident_spike_delta"] >= 1

    def test_production_env(self):
        policy = {"active_environment": "staging", "environments": {"staging": {"incident_spike_delta": 3}}}
        r = _resolve_compliance_policy(policy)
        assert r["environment"] == "staging"
        assert r["incident_spike_delta"] == 3

    def test_missing_env_fallsback_production(self):
        r = _resolve_compliance_policy({"environments": {}}, environment="staging")
        assert r["environment"] == "staging"

    def test_suppressions_expired_filtered(self):
        now_iso = datetime.now(tz=timezone.utc).isoformat()
        future_iso = (datetime.now(tz=timezone.utc) + timedelta(hours=24)).isoformat()
        policy = {"suppressions": [
            {"kind": "all", "expires_at": now_iso},
            {"kind": "feature", "value": "x", "expires_at": future_iso},
        ]}
        r = _resolve_compliance_policy(policy)
        assert len(r["suppressions"]) == 1

    def test_invalid_suppression_skipped(self):
        future_iso = (datetime.now(tz=timezone.utc) + timedelta(hours=24)).isoformat()
        policy = {"suppressions": ["not-a-dict", {"kind": "all", "expires_at": future_iso}]}
        r = _resolve_compliance_policy(policy)
        assert len(r["suppressions"]) == 1

    def test_critical_flags_from_policy(self):
        r = _resolve_compliance_policy({"critical_feature_flags": ["a", "b"]})
        assert "a" in r["critical_feature_flags"]

    def test_critical_flags_empty_default(self):
        r = _resolve_compliance_policy({"critical_feature_flags": []})
        assert len(r["critical_feature_flags"]) > 0

    def test_environment_param(self):
        r = _resolve_compliance_policy({"active_environment": "production"}, environment="staging")
        assert r["environment"] == "staging"


# ── _is_drift_signal_suppressed ────────────────────────────────────────────────

class TestIsDriftSignalSuppressed:
    def test_kind_all(self):
        assert _is_drift_signal_suppressed("f", "x", [{"kind": "all"}])

    def test_kind_feature_match(self):
        assert _is_drift_signal_suppressed("feature", "a", [{"kind": "feature", "value": "a"}])

    def test_kind_feature_no_match(self):
        assert not _is_drift_signal_suppressed("feature", "a", [{"kind": "feature", "value": "b"}])

    def test_kind_metric_match(self):
        assert _is_drift_signal_suppressed("metric_alert", "m", [{"kind": "metric_alert", "value": "m"}])

    def test_empty(self):
        assert not _is_drift_signal_suppressed("f", "x", [])

    def test_kind_severity(self):
        assert _is_drift_signal_suppressed("severity", "h", [{"kind": "severity", "value": "h"}])


# ── _compare_snapshot_payloads ─────────────────────────────────────────────────

class TestCompareSnapshotPayloads:
    def test_metric_delta(self):
        base = {"audit": {"count": 10}, "incidents": {"summary": {}}}
        target = {"audit": {"count": 20}, "incidents": {"summary": {}}}
        r = _compare_snapshot_payloads(base, target)
        assert r["metrics"]["audit_count"]["delta"] == 10

    def test_feature_changes(self):
        base = {"config": {"features_enabled": {"a": True, "b": False}}}
        target = {"config": {"features_enabled": {"a": False, "b": True}}}
        r = _compare_snapshot_payloads(base, target)
        assert r["feature_changes_count"] == 2

    def test_no_changes(self):
        base = {"audit": {"count": 5}, "incidents": {"summary": {}}, "config": {"features_enabled": {"f": True}}}
        r = _compare_snapshot_payloads(base, base)
        assert r["feature_changes_count"] == 0

    def test_non_numeric_delta(self):
        base = {"audit": {"count": "x"}, "incidents": {"summary": {}}}
        target = {"audit": {"count": 10}, "incidents": {"summary": {}}}
        r = _compare_snapshot_payloads(base, target)
        assert r["metrics"]["audit_count"]["delta"] is None


# ── _assess_config_drift ──────────────────────────────────────────────────────

class TestAssessConfigDrift:
    def test_no_drift(self):
        r = _assess_config_drift({}, {}, [])
        assert r["has_drift"] is False
        assert r["severity"] == "low"

    def test_critical_disabled(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": {"f1"},
                "critical_feature_disabled_force": True,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift(
                {"incident_count": 0, "mtta_minutes": 0, "mttr_minutes": 0},
                {"incident_count": 0, "mtta_minutes": 0, "mttr_minutes": 0},
                [{"feature": "f1", "before": True, "after": False}],
            )
        assert r["severity"] == "critical"
        assert any("criticos" in x for x in r["reasons"])

    def test_high_many_critical_changes(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": {"f1", "f2"},
                "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift(
                {"incident_count": 5}, {"incident_count": 5},
                [{"feature": "f1", "before": False, "after": True},
                 {"feature": "f2", "before": True, "after": False}],
            )
        assert r["severity"] == "high"
        assert any("criticos cambiaron" in x for x in r["reasons"])

    def test_medium_one_critical_change(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": {"f1", "f2"},
                "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift({"incident_count": 5}, {"incident_count": 5},
                [{"feature": "f1", "before": False, "after": True}])
        assert r["severity"] == "medium"

    def test_medium_three_feature_changes(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": set(),
                "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift({"incident_count": 5}, {"incident_count": 5},
                [{"feature": f"f{i}", "before": False, "after": True} for i in range(3)])
        assert r["severity"] == "medium"
        assert any("simultaneos" in x for x in r["reasons"])

    def test_incident_spike(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": set(), "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift(
                {"incident_count": 0, "mtta_minutes": 0, "mttr_minutes": 0},
                {"incident_count": 10, "mtta_minutes": 0, "mttr_minutes": 0}, [])
        assert "incident_count_spike" in r["metric_alerts"]

    def test_mtta_regression(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": set(), "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.25,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift(
                {"incident_count": 5, "mtta_minutes": 10, "mttr_minutes": 0},
                {"incident_count": 5, "mtta_minutes": 30, "mttr_minutes": 0}, [])
        assert "mtta_regression" in r["metric_alerts"]

    def test_mttr_regression(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": set(), "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.25, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift(
                {"incident_count": 5, "mtta_minutes": 0, "mttr_minutes": 10},
                {"incident_count": 5, "mtta_minutes": 0, "mttr_minutes": 30}, [])
        assert "mttr_regression" in r["metric_alerts"]

    def test_dual_metric_alerts_escalates(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": set(), "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.25,
                "mttr_regression_pct": 0.25, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift(
                {"incident_count": 0, "mtta_minutes": 10, "mttr_minutes": 10},
                {"incident_count": 10, "mtta_minutes": 30, "mttr_minutes": 30}, [])
        assert len(r["metric_alerts"]) >= 2
        assert r["severity"] == "high"

    def test_suppressed_feature_changes(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": set(), "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [{"kind": "feature", "value": "a"}],
            }
            r = _assess_config_drift({"incident_count": 5}, {"incident_count": 5},
                [{"feature": "a", "before": False, "after": True}])
        assert len(r["active"]["feature_changes"]) == 0

    def test_non_critical_changes_separated(self):
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": {"crit"}, "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [],
            }
            r = _assess_config_drift({"incident_count": 5}, {"incident_count": 5},
                [{"feature": "abc", "before": False, "after": True}])
        assert len(r["non_critical_feature_changes"]) == 1


# ── _resolve_compare_pair ──────────────────────────────────────────────────────

class TestResolveComparePair:
    def test_by_ids(self):
        rows = [{"snapshot_id": "1"}, {"snapshot_id": "2"}, {"snapshot_id": "3"}]
        a, b = _resolve_compare_pair(rows, "1", "3")
        assert a["snapshot_id"] == "1"
        assert b["snapshot_id"] == "3"

    def test_auto_last_two_sorted(self):
        rows = [{"snapshot_id": "a", "recorded_at": "2026-01-01T00:00:00Z"},
                {"snapshot_id": "b", "recorded_at": "2026-01-03T00:00:00Z"},
                {"snapshot_id": "c", "recorded_at": "2026-01-02T00:00:00Z"}]
        a, b = _resolve_compare_pair(rows, None, None)
        # Sorted by recorded_at: a (Jan 1), c (Jan 2), b (Jan 3) -> last two: c, b
        assert a["snapshot_id"] in ("c", "a"), f"got {a}"
        assert b["snapshot_id"] == "b"

    def test_less_than_two_422(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _resolve_compare_pair([{"snapshot_id": "1"}], None, None)
        assert exc.value.status_code == 422

    def test_not_found_404(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _resolve_compare_pair([{"snapshot_id": "1"}], "x", "1")
        assert exc.value.status_code == 404


# ── _cleanup_snapshot_history ──────────────────────────────────────────────────

class TestCleanupSnapshotHistory:
    def test_removes_old(self):
        now = datetime.now(tz=timezone.utc)
        old_iso = (now - timedelta(days=100)).isoformat()
        recent_iso = (now - timedelta(days=10)).isoformat()
        rows = [{"recorded_at": old_iso}, {"recorded_at": recent_iso}]
        r = _cleanup_snapshot_history(rows, retain_days=30)
        assert r["removed"] == 1
        assert r["retained"] == 1

    def test_all_kept(self):
        recent_iso = (datetime.now(tz=timezone.utc) - timedelta(days=5)).isoformat()
        rows = [{"recorded_at": recent_iso}]
        r = _cleanup_snapshot_history(rows, retain_days=30)
        assert r["removed"] == 0
        assert r["retained"] == 1

    def test_clamps_safe_days(self):
        r = _cleanup_snapshot_history([], retain_days=9999)
        assert r["retain_days"] == 3650


# ── _maybe_emit_snapshot_drift_alert ──────────────────────────────────────────

class TestMaybeEmitSnapshotDriftAlert:
    def test_no_previous(self):
        assert _maybe_emit_snapshot_drift_alert(previous_entry=None, current_entry={}) is None

    def test_non_dict_snapshots(self):
        r = _maybe_emit_snapshot_drift_alert(
            previous_entry={"snapshot": "s"}, current_entry={"snapshot": "s"})
        assert r is None

    def test_returns_drift_info(self):
        r = _maybe_emit_snapshot_drift_alert(
            previous_entry={"snapshot_id": "a", "snapshot": {"audit": {}, "incidents": {"summary": {}}, "config": {"features_enabled": {}}}},
            current_entry={"snapshot_id": "b", "snapshot": {"audit": {}, "incidents": {"summary": {}}, "config": {"features_enabled": {}}}},
        )
        assert isinstance(r, dict)
        assert r["from_snapshot_id"] == "a"
        assert r["to_snapshot_id"] == "b"


# ── _weekly_snapshot_summary ───────────────────────────────────────────────────

class TestWeeklySnapshotSummary:
    def test_empty(self):
        r = _weekly_snapshot_summary([], weeks=4)
        assert len(r) == 4

    def test_with_data(self):
        now = datetime.now(tz=timezone.utc)
        rows = [{"recorded_at": now.isoformat(), "summary": {"has_anomaly": True, "critical_incidents": 2}}]
        r = _weekly_snapshot_summary(rows, weeks=4)
        total = sum(b["snapshots"] for b in r)
        assert total >= 1

    def test_drift_critical(self):
        rows = [{"recorded_at": datetime.now(tz=timezone.utc).isoformat(),
                 "summary": {}, "drift_from_previous": {"severity": "critical", "risk_score": 90}}]
        r = _weekly_snapshot_summary(rows, weeks=4)
        assert sum(b["critical_drift_alerts"] for b in r) >= 1

    def test_drift_high(self):
        rows = [{"recorded_at": datetime.now(tz=timezone.utc).isoformat(),
                 "summary": {}, "drift_from_previous": {"severity": "high", "risk_score": 70}}]
        r = _weekly_snapshot_summary(rows, weeks=4)
        assert sum(b["high_drift_alerts"] for b in r) >= 1


# ── _normalize_compliance_policy_update ────────────────────────────────────────

class TestNormalizeCompliancePolicyUpdate:
    def test_empty_returns_current(self):
        cur = {"active_environment": "production", "environments": {}, "suppressions": []}
        r = _normalize_compliance_policy_update({}, cur)
        assert r["active_environment"] == "production"

    def test_update_env(self):
        cur = {"active_environment": "production", "environments": {}, "suppressions": []}
        r = _normalize_compliance_policy_update({"active_environment": "staging"}, cur)
        assert r["active_environment"] == "staging"

    def test_invalid_env(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_compliance_policy_update({"active_environment": "bad"}, {})
        assert exc.value.status_code == 422

    def test_invalid_flags_type(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_compliance_policy_update({"critical_feature_flags": "str"}, {})
        assert exc.value.status_code == 422

    def test_update_flags_dedup(self):
        cur = {"active_environment": "production", "environments": {}, "suppressions": []}
        r = _normalize_compliance_policy_update({"critical_feature_flags": ["a", "b", "a"]}, cur)
        assert r["critical_feature_flags"] == ["a", "b"]

    def test_invalid_environments_type(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_compliance_policy_update({"environments": "not-dict"}, {})
        assert exc.value.status_code == 422

    def test_invalid_env_key(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_compliance_policy_update({"environments": {"bad": {}}}, {})
        assert exc.value.status_code == 422

    def test_merge_environments(self):
        cur = {"active_environment": "production", "environments": {"staging": {"incident_spike_delta": 3}}, "suppressions": []}
        r = _normalize_compliance_policy_update({"environments": {"staging": {"mtta_regression_pct": 0.5}}}, cur)
        assert r["environments"]["staging"]["incident_spike_delta"] == 3
        assert r["environments"]["staging"]["mtta_regression_pct"] == 0.5


# ── _normalize_suppression_payload ─────────────────────────────────────────────

class TestNormalizeSuppressionPayload:
    def test_kind_all(self):
        r = _normalize_suppression_payload({"kind": "all"}, "actor_1")
        assert r["kind"] == "all"
        assert r["created_by"] == "actor_1"

    def test_kind_feature(self):
        r = _normalize_suppression_payload({"kind": "feature", "value": "flag_x"}, "actor_1")
        assert r["kind"] == "feature"
        assert r["value"] == "flag_x"

    def test_invalid_kind(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_suppression_payload({"kind": "invalid"}, "actor_1")
        assert exc.value.status_code == 422

    def test_missing_value_non_all(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_suppression_payload({"kind": "feature"}, "actor_1")
        assert exc.value.status_code == 422

    def test_not_dict(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_suppression_payload("string", "a")
        assert exc.value.status_code == 422

    def test_invalid_expires_hours(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_suppression_payload({"kind": "all", "expires_in_hours": "bad"}, "a")
        assert exc.value.status_code == 422

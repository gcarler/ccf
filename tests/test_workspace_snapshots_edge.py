"""Remaining edge cases for _snapshots.py — suppression, notification, weekly."""
from __future__ import annotations

import pytest

from backend.api.workspace_shared._snapshots import (
    _assess_config_drift,
    _maybe_emit_snapshot_drift_alert,
    _weekly_snapshot_summary,
    _normalize_compliance_policy_update,
)
from unittest.mock import patch


class TestAssessConfigDriftSuppressed:
    def test_suppressed_severity(self):
        """Lines 372-373: suppression lowers severity to low."""
        with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
            m.return_value = {
                "critical_feature_flags": set(), "critical_feature_disabled_force": False,
                "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                "suppressions": [{"kind": "severity", "value": "medium"}],
            }
            r = _assess_config_drift(
                {"incident_count": 5}, {"incident_count": 5},
                [{"feature": "a", "before": False, "after": True},
                 {"feature": "b", "before": True, "after": False},
                 {"feature": "c", "before": False, "after": True}],
            )
        assert r["effective_severity"] == "low"
        assert r["effective_has_drift"] is False


class TestMaybeEmitHighSeverity:
    def test_critical_drift_triggers_notification(self):
        """Line 477: critical drift alert calls _append_notification."""
        base_snap = {"audit": {"count": 5}, "incidents": {"summary": {}},
                     "config": {"features_enabled": {"f1": True}}}
        target_snap = {"audit": {"count": 5}, "incidents": {"summary": {}},
                       "config": {"features_enabled": {"f1": False}}}
        with patch("backend.api.workspace_shared._snapshots._append_notification") as mock_notif:
            with patch("backend.api.workspace_shared._snapshots._resolve_compliance_policy") as m:
                m.return_value = {
                    "critical_feature_flags": {"f1"},
                    "critical_feature_disabled_force": True,
                    "incident_spike_delta": 5, "mtta_regression_pct": 0.01,
                    "mttr_regression_pct": 0.01, "critical_feature_change_count_high": 2,
                    "suppressions": [],
                }
                r = _maybe_emit_snapshot_drift_alert(
                    previous_entry={"snapshot_id": "a", "snapshot": base_snap},
                    current_entry={"snapshot_id": "b", "snapshot": target_snap},
                )
        assert r is not None
        assert r["severity"] in ("high", "critical")
        mock_notif.assert_called_once()


class TestWeeklySummaryEdgeCases:
    def test_no_recorded_at_skipped(self):
        """Lines 534, 538: row without recorded_at is skipped."""
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        rows = [
            {"no_date": True},  # no recorded_at
            {"recorded_at": now.isoformat()},
        ]
        r = _weekly_snapshot_summary(rows, weeks=4)
        total = sum(b["snapshots"] for b in r)
        assert total >= 1


class TestNormalizePolicyUpdateEdgeCases:
    def test_env_values_not_dict_raises(self):
        """Line 613: env_values must be a dict."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_compliance_policy_update(
                {"environments": {"staging": "not-a-dict"}}, {}
            )
        assert exc.value.status_code == 422

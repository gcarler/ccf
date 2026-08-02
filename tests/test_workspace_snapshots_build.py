"""Cover _build_compliance_snapshot and remaining edge cases."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from backend.api.workspace_shared._snapshots import (
    _build_compliance_snapshot,
    _normalize_compliance_policy_update,
    _weekly_snapshot_summary,
)


class TestBuildComplianceSnapshot:
    def test_build_full_snapshot(self):
        """Cover _build_compliance_snapshot (lines 723-842) with mocked deps."""
        mock_workspace_config = {
            "features_enabled": {"f1": True},
            "feature_rules": {"f1": "rule1"},
            "compliance_policy": {"active_environment": "production"},
        }

        mock = MagicMock()
        mock.return_value = mock_workspace_config

        with patch.multiple(
            "backend.api.workspace_shared._snapshots",
            _load_workspace_config=MagicMock(return_value=mock_workspace_config),
            _load_incidents=MagicMock(return_value=[{"id": "inc1"}, {"id": "inc2"}]),
            _read_audit_events=MagicMock(return_value=[{"actor": "u1", "action": "login"}]),
            _enrich_audit_rows=MagicMock(return_value=[{"actor": "u1", "action": "login", "enriched": True}]),
            _detect_anomalies=MagicMock(return_value={"has_anomaly": False, "count": 0}),
            _period_bounds=MagicMock(return_value=("s", "e", "ps", "pe", "weekly")),
            _period_incident_stats=MagicMock(return_value={"created": 5, "mtta_minutes": 10}),
            _summarize_incidents=MagicMock(return_value={"total": 2}),
            _summarize_audit=MagicMock(return_value={"total": 1}),
            _incident_daily_trends=MagicMock(return_value=[{"date": "2026-07-01", "count": 1}]),
            _read_notifications=MagicMock(return_value=[{"type": "test"}]),
            _pct_delta=MagicMock(return_value=0.0),
            _now_iso=MagicMock(return_value="2026-07-29T12:00:00Z"),
            _resolve_compliance_policy=MagicMock(return_value={"environment": "production", "critical_feature_flags": [], "suppressions": []}),
        ):
            result = _build_compliance_snapshot(
                actor_id="test_actor",
                environment="production",
                audit_limit=100,
                incident_limit=100,
                lookback_hours=24,
                actor_threshold=5,
                action_threshold=10,
            )

        assert result["schema_version"] is not None
        assert result["requested_by"] == "test_actor"
        assert "signature" in result
        assert result["inputs"]["audit_limit"] == 100
        assert result["inputs"]["lookback_hours"] == 24
        assert result["inputs"]["actor_threshold"] == 5


class TestWeeklySummaryOutOfRange:
    def test_row_outside_buckets_skipped(self):
        """Line 538: row with week outside the buckets range is skipped."""
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        # A row from 3 years ago -> outside 4-week buckets
        old = __import__("datetime").datetime(2023, 1, 15, tzinfo=__import__("datetime").timezone.utc)
        rows = [{"recorded_at": old.isoformat(), "summary": {}}]
        r = _weekly_snapshot_summary(rows, weeks=4)
        total = sum(b["snapshots"] for b in r)
        assert total == 0  # old row excluded from 4-week window


class TestNormalizePolicyUpdateNonDictPayload:
    def test_non_dict_payload_raises(self):
        """Line 567: non-dict payload raises 422."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            _normalize_compliance_policy_update("string-payload", {})
        assert exc.value.status_code == 422

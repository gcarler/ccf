"""Final edge cases for _storage.py."""
from __future__ import annotations

import json
from unittest.mock import patch

from backend.api.workspace_shared._storage import (
    _load_workspace_config,
    _read_notifications,
    _read_snapshot_history,
)


class TestLoadConfigFinalEdges:
    def test_feature_rule_dict_merges(self):
        """Line 48: dict value merges with base_rule."""
        data = {"features_enabled": {}, "feature_rules": {"f1": {"rollout_percent": 50}}}
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps(data)
            r = _load_workspace_config()
        assert "f1" in r["feature_rules"]

    def test_env_value_dict_merges(self):
        """Lines 62-64: env config dict merges with default."""
        data = {
            "features_enabled": {},
            "compliance_policy": {
                "environments": {"staging": {"incident_spike_delta": 3}},
            },
        }
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps(data)
            r = _load_workspace_config()
        policy = r["compliance_policy"]
        assert "staging" in policy["environments"]
        assert policy["environments"]["staging"]["incident_spike_delta"] == 3

    def test_non_dict_data_returns_default(self):
        """Line 109: JSON exists but not a dict -> return default."""
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps(["not-a-dict"])
            r = _load_workspace_config()
        assert "features_enabled" in r


class TestReadNotificationsLimit:
    def test_limit_applied(self):
        """Line 231: clamped limit applied to returned rows."""
        rows = [{"i": i} for i in range(50)]
        content = "\n".join(json.dumps(r) for r in rows)
        with patch("backend.api.workspace_shared._storage.NOTIFICATIONS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = content
            r = _read_notifications(limit=10)
        assert len(r) == 10


class TestReadSnapshotHistoryLimit:
    def test_limit_applied(self):
        """Line 259: clamped limit applied to returned rows."""
        rows = [{"i": i} for i in range(100)]
        content = "\n".join(json.dumps(r) for r in rows)
        with patch("backend.api.workspace_shared._storage.SNAPSHOT_HISTORY_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = content
            r = _read_snapshot_history(limit=10)
        assert len(r) == 10

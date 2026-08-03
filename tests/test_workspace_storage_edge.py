"""Remaining edge cases for _storage.py."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.api.workspace_shared._storage import (
    _load_workspace_config,
    _load_incidents,
    _read_notifications,
    _read_snapshot_history,
)


class TestLoadWorkspaceConfigEdges:
    def test_feature_rules_non_dict_value(self):
        """Line 49: feature rule value is not a dict -> use base_rule."""
        data = {"features_enabled": {}, "feature_rules": {"f1": "not-a-dict"}}
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps(data)
            r = _load_workspace_config()
        assert "f1" in r["feature_rules"]

    def test_memory_error_re_raised(self):
        """Line 105: MemoryError propagates."""
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.side_effect = MemoryError("oom")
            with pytest.raises(MemoryError):
                _load_workspace_config()

    def test_generic_exception_returns_default(self):
        """Line 107-108: any other error returns default."""
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.side_effect = PermissionError("denied")
            r = _load_workspace_config()
        assert "features_enabled" in r


class TestLoadIncidentsEdges:
    def test_memory_error_re_raised(self):
        """Line 131: MemoryError propagates."""
        with patch("backend.api.workspace_shared._storage.INCIDENTS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.side_effect = MemoryError("oom")
            with pytest.raises(MemoryError):
                _load_incidents()


class TestReadNotificationsEdges:
    def test_skips_bad_json_lines(self):
        """Lines 234-235: JSONDecodeError skips the line."""
        with patch("backend.api.workspace_shared._storage.NOTIFICATIONS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = "valid\nbad\n{\"a\":1}\n"
            r = _read_notifications()
        assert len(r) == 1  # only valid {"a":1}


class TestReadSnapshotHistoryEdges:
    def test_skips_bad_json_lines(self):
        """Lines 262-263: JSONDecodeError skips the line."""
        with patch("backend.api.workspace_shared._storage.SNAPSHOT_HISTORY_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = "bad\n{\"b\":2}\n"
            r = _read_snapshot_history()
        assert len(r) == 1

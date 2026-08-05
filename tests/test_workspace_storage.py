"""Tests for _storage.py."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from backend.api.workspace_shared._storage import (
    _append_audit_event,
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
    _save_workspace_config,
)

# ── Pure helpers ───────────────────────────────────────────────────────────────

class TestNowIso:
    def test_returns_iso_string(self):
        r = _now_iso()
        assert "T" in r
        assert r.endswith("+00:00") or "+" in r


class TestJsonCanonical:
    def test_sorted_keys(self):
        r = _json_canonical({"b": 2, "a": 1})
        assert r == '{"a":1,"b":2}'

    def test_ensure_ascii(self):
        r = _json_canonical({"ñ": "é"})
        assert "\\u00f1" in r


# ── _load_workspace_config ─────────────────────────────────────────────────────

class TestLoadWorkspaceConfig:
    def test_file_not_found_returns_default(self):
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = False
            r = _load_workspace_config()
        assert "features_enabled" in r

    def test_invalid_json_returns_default(self):
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = "invalid json"
            r = _load_workspace_config()
        assert "features_enabled" in r

    def test_valid_config(self):
        data = {"features_enabled": {"f1": True}}
        with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps(data)
            r = _load_workspace_config()
        assert r["features_enabled"]["f1"] is True


# ── _save_workspace_config ─────────────────────────────────────────────────────

class TestSaveWorkspaceConfig:
    def test_writes_to_file(self):
        config = {"features_enabled": {"f1": True}}
        with patch("backend.api.workspace_shared._storage.DATA_DIR") as mock_dir:
            mock_dir.mkdir.return_value = None
            with patch("backend.api.workspace_shared._storage.file_lock"):
                with patch("backend.api.workspace_shared._storage.FLAGS_FILE") as mock_f:
                    _save_workspace_config(config)
                    mock_f.write_text.assert_called_once()


# ── _load_incidents ────────────────────────────────────────────────────────────

class TestLoadIncidents:
    def test_file_not_found_returns_empty(self):
        with patch("backend.api.workspace_shared._storage.INCIDENTS_FILE") as mock_f:
            mock_f.exists.return_value = False
            assert _load_incidents() == []

    def test_invalid_json_returns_empty(self):
        with patch("backend.api.workspace_shared._storage.INCIDENTS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = "invalid"
            assert _load_incidents() == []

    def test_non_list_returns_empty(self):
        with patch("backend.api.workspace_shared._storage.INCIDENTS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps({"not": "list"})
            assert _load_incidents() == []

    def test_skips_non_dict_items(self):
        with patch("backend.api.workspace_shared._storage.INCIDENTS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps(["string", {"id": "1"}])
            r = _load_incidents()
        assert len(r) == 1
        assert r[0]["id"] == "1"

    def test_normalizes_fields(self):
        with patch("backend.api.workspace_shared._storage.INCIDENTS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = json.dumps([{"id": "inc1", "kind": "spike"}])
            r = _load_incidents()
        assert r[0]["id"] == "inc1"
        assert r[0]["status"] == "open"
        assert r[0]["severity"] == "low"


# ── _save_incidents ────────────────────────────────────────────────────────────

class TestSaveIncidents:
    def test_writes_to_file(self):
        with patch("backend.api.workspace_shared._storage.DATA_DIR"):
            with patch("backend.api.workspace_shared._storage.file_lock"):
                with patch("backend.api.workspace_shared._storage.INCIDENTS_FILE") as mock_f:
                    _save_incidents([{"id": "1"}])
                    mock_f.write_text.assert_called_once()


# ── _read_audit_events ─────────────────────────────────────────────────────────

class TestReadAuditEvents:
    def test_file_not_found(self):
        with patch("backend.api.workspace_shared._storage.AUDIT_FILE") as mock_f:
            mock_f.exists.return_value = False
            assert _read_audit_events() == []

    def test_reads_lines(self):
        lines = [json.dumps({"a": 1}), json.dumps({"b": 2})]
        with patch("backend.api.workspace_shared._storage.AUDIT_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = "\n".join(lines)
            r = _read_audit_events()
        assert len(r) == 2

    def test_skips_empty_lines_and_bad_json(self):
        content = "valid\n\nbad\n{\"a\":1}\n"
        with patch("backend.api.workspace_shared._storage.AUDIT_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = content
            r = _read_audit_events()
        assert len(r) == 1  # only {"a": 1} is valid JSON dict
        assert r[0]["a"] == 1


# ── _append_audit_event ────────────────────────────────────────────────────────

class TestAppendAuditEvent:
    def test_appends_to_file(self):
        with patch("backend.api.workspace_shared._storage.DATA_DIR") as mock_dir:
            mock_dir.mkdir.return_value = None
            with patch("backend.api.workspace_shared._storage.AUDIT_FILE") as mock_f:
                mock_f.open.return_value.__enter__.return_value = MagicMock()
                _append_audit_event({"action": "test"})
                mock_f.open.assert_called_once()


# ── _append_notification ───────────────────────────────────────────────────────

class TestAppendNotification:
    def test_appends_to_file(self):
        with patch("backend.api.workspace_shared._storage.DATA_DIR"):
            with patch("backend.api.workspace_shared._storage.NOTIFICATIONS_FILE") as mock_f:
                mock_f.open.return_value.__enter__.return_value = MagicMock()
                _append_notification({"type": "alert"})
                mock_f.open.assert_called_once()


# ── _read_notifications ────────────────────────────────────────────────────────

class TestReadNotifications:
    def test_file_not_found(self):
        with patch("backend.api.workspace_shared._storage.NOTIFICATIONS_FILE") as mock_f:
            mock_f.exists.return_value = False
            assert _read_notifications() == []

    def test_reads_valid_lines(self):
        with patch("backend.api.workspace_shared._storage.NOTIFICATIONS_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = '{"a":1}\n{"b":2}\n'
            assert len(_read_notifications()) == 2


# ── _append_snapshot_history ───────────────────────────────────────────────────

class TestAppendSnapshotHistory:
    def test_appends_to_file(self):
        with patch("backend.api.workspace_shared._storage.DATA_DIR"):
            with patch("backend.api.workspace_shared._storage.SNAPSHOT_HISTORY_FILE") as mock_f:
                mock_f.open.return_value.__enter__.return_value = MagicMock()
                _append_snapshot_history({"v": 1})
                mock_f.open.assert_called_once()


# ── _read_snapshot_history ─────────────────────────────────────────────────────

class TestReadSnapshotHistory:
    def test_file_not_found(self):
        with patch("backend.api.workspace_shared._storage.SNAPSHOT_HISTORY_FILE") as mock_f:
            mock_f.exists.return_value = False
            assert _read_snapshot_history() == []

    def test_reads_valid_lines(self):
        with patch("backend.api.workspace_shared._storage.SNAPSHOT_HISTORY_FILE") as mock_f:
            mock_f.exists.return_value = True
            mock_f.read_text.return_value = '{"a":1}\n{"b":2}\n'
            assert len(_read_snapshot_history()) == 2


# ── _save_snapshot_history ─────────────────────────────────────────────────────

class TestSaveSnapshotHistory:
    def test_writes_rows(self):
        with patch("backend.api.workspace_shared._storage.DATA_DIR"):
            with patch("backend.api.workspace_shared._storage.file_lock"):
                with patch("backend.api.workspace_shared._storage.SNAPSHOT_HISTORY_FILE") as mock_f:
                    _save_snapshot_history([{"id": "1"}])
                    mock_f.open.assert_called_once()


# ── _append_incident_history ───────────────────────────────────────────────────

class TestAppendIncidentHistory:
    def test_appends_to_existing_history(self):
        incident = {"history": [{"at": "old"}]}
        _append_incident_history(incident, event="test", actor_id="a")
        assert len(incident["history"]) == 2
        assert incident["history"][-1]["event"] == "test"
        assert incident["history"][-1]["by"] == "a"

    def test_creates_history_list(self):
        incident = {}
        _append_incident_history(incident, event="first", actor_id="b")
        assert len(incident["history"]) == 1

    def test_with_note_and_metadata(self):
        incident = {}
        _append_incident_history(incident, event="e", actor_id="c",
                                  note="hello", metadata={"key": "val"})
        assert incident["history"][-1]["note"] == "hello"
        assert incident["history"][-1]["metadata"]["key"] == "val"

    def test_truncates_to_50(self):
        incident = {"history": [{"at": f"e{i}"} for i in range(60)]}
        _append_incident_history(incident, event="last", actor_id="d")
        assert len(incident["history"]) <= 50

"""
Extended unit tests for backend.api.workspace_shared._storage.
Covers all read/write and persistence functions.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from backend.api.workspace_shared import _storage as storage


class TestLoadIncidents:
    def test_no_file_returns_empty(self, monkeypatch):
        monkeypatch.setattr(storage, "INCIDENTS_FILE", Path(f"/tmp/test_inc_{uuid.uuid4().hex}.json"))
        result = storage._load_incidents()
        assert result == []

    def test_invalid_json_returns_empty(self, monkeypatch, tmp_path):
        f = tmp_path / "incidents.json"
        f.write_text("invalid json", encoding="utf-8")
        monkeypatch.setattr(storage, "INCIDENTS_FILE", f)
        result = storage._load_incidents()
        assert result == []

    def test_non_list_json_returns_empty(self, monkeypatch, tmp_path):
        f = tmp_path / "incidents.json"
        f.write_text('{"not": "list"}', encoding="utf-8")
        monkeypatch.setattr(storage, "INCIDENTS_FILE", f)
        result = storage._load_incidents()
        assert result == []

    def test_list_with_items(self, monkeypatch, tmp_path):
        f = tmp_path / "incidents.json"
        data = [{"id": "1", "kind": "test", "key": "k1"}]
        f.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(storage, "INCIDENTS_FILE", f)
        result = storage._load_incidents()
        assert len(result) == 1
        assert result[0]["kind"] == "test"

    def test_skips_non_dict_items(self, monkeypatch, tmp_path):
        f = tmp_path / "incidents.json"
        data = [{"id": "1"}, "string_item", {"id": "2"}]
        f.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(storage, "INCIDENTS_FILE", f)
        result = storage._load_incidents()
        assert len(result) == 2


class TestSaveIncidents:
    def test_saves_and_loads(self, monkeypatch, tmp_path):
        f = tmp_path / "incidents.json"
        monkeypatch.setattr(storage, "INCIDENTS_FILE", f)
        incidents = [{"id": "1", "kind": "test", "key": "k1"}]
        storage._save_incidents(incidents)
        assert f.exists()
        loaded = json.loads(f.read_text(encoding="utf-8"))
        assert len(loaded) == 1


class TestLoadWorkspaceConfig:
    def test_no_file_returns_default(self, monkeypatch):
        monkeypatch.setattr(storage, "FLAGS_FILE", Path(f"/tmp/test_flags_{uuid.uuid4().hex}.json"))
        from backend.api.workspace_shared import DEFAULT_WORKSPACE_CONFIG
        result = storage._load_workspace_config()
        assert result == DEFAULT_WORKSPACE_CONFIG

    def test_with_valid_data(self, monkeypatch, tmp_path):
        f = tmp_path / "flags.json"
        f.write_text(json.dumps({"features_enabled": {"feat_x": True}}), encoding="utf-8")
        monkeypatch.setattr(storage, "FLAGS_FILE", f)
        result = storage._load_workspace_config()
        assert isinstance(result, dict)
        assert "features_enabled" in result

    def test_invalid_json_returns_default(self, monkeypatch, tmp_path):
        f = tmp_path / "flags.json"
        f.write_text("not json", encoding="utf-8")
        monkeypatch.setattr(storage, "FLAGS_FILE", f)
        from backend.api.workspace_shared import DEFAULT_WORKSPACE_CONFIG
        result = storage._load_workspace_config()
        assert result == DEFAULT_WORKSPACE_CONFIG

    def test_merge_feature_rules(self, monkeypatch, tmp_path):
        f = tmp_path / "flags.json"
        data = {"feature_rules": {"rule_a": {"enabled": True}}}
        f.write_text(json.dumps(data), encoding="utf-8")
        monkeypatch.setattr(storage, "FLAGS_FILE", f)
        result = storage._load_workspace_config()
        assert "feature_rules" in result
        assert "rule_a" in result["feature_rules"]


class TestSaveWorkspaceConfig:
    def test_saves_config(self, monkeypatch, tmp_path):
        f = tmp_path / "flags.json"
        monkeypatch.setattr(storage, "FLAGS_FILE", f)
        storage._save_workspace_config({"test": True})
        assert f.exists()
        loaded = json.loads(f.read_text(encoding="utf-8"))
        assert loaded["test"] is True


class TestReadAuditEvents:
    def test_no_file_returns_empty(self, monkeypatch):
        monkeypatch.setattr(storage, "AUDIT_FILE", Path(f"/tmp/test_audit_{uuid.uuid4().hex}.json"))
        result = storage._read_audit_events()
        assert result == []

    def test_parses_valid_lines(self, monkeypatch, tmp_path):
        f = tmp_path / "audit.jsonl"
        f.write_text('{"action":"create"}\n{"action":"update"}', encoding="utf-8")
        monkeypatch.setattr(storage, "AUDIT_FILE", f)
        result = storage._read_audit_events()
        assert len(result) == 2

    def test_skips_invalid_lines(self, monkeypatch, tmp_path):
        f = tmp_path / "audit.jsonl"
        f.write_text('{"action":"create"}\ninvalid\n{"action":"update"}', encoding="utf-8")
        monkeypatch.setattr(storage, "AUDIT_FILE", f)
        result = storage._read_audit_events()
        assert len(result) == 2

    def test_skips_non_dict_lines(self, monkeypatch, tmp_path):
        f = tmp_path / "audit.jsonl"
        f.write_text('"just_a_string"', encoding="utf-8")
        monkeypatch.setattr(storage, "AUDIT_FILE", f)
        result = storage._read_audit_events()
        assert result == []

    def test_limits_results(self, monkeypatch, tmp_path):
        f = tmp_path / "audit.jsonl"
        lines = '\n'.join([f'{{"n":{i}}}' for i in range(50)])
        f.write_text(lines, encoding="utf-8")
        monkeypatch.setattr(storage, "AUDIT_FILE", f)
        result = storage._read_audit_events(limit=10)
        assert len(result) == 10


class TestAppendAuditEvent:
    def test_appends_line(self, monkeypatch, tmp_path):
        f = tmp_path / "audit.jsonl"
        monkeypatch.setattr(storage, "AUDIT_FILE", f)
        storage._append_audit_event({"action": "test"})
        content = f.read_text(encoding="utf-8").strip()
        assert content
        assert "test" in content


class TestReadNotifications:
    def test_no_file_returns_empty(self, monkeypatch):
        monkeypatch.setattr(storage, "NOTIFICATIONS_FILE", Path(f"/tmp/test_notif_{uuid.uuid4().hex}.json"))
        result = storage._read_notifications()
        assert result == []

    def test_reads_lines(self, monkeypatch, tmp_path):
        f = tmp_path / "notifications.jsonl"
        f.write_text('{"type":"alert"}\n{"type":"info"}', encoding="utf-8")
        monkeypatch.setattr(storage, "NOTIFICATIONS_FILE", f)
        result = storage._read_notifications()
        assert len(result) == 2

    def test_limits(self, monkeypatch, tmp_path):
        f = tmp_path / "notifications.jsonl"
        lines = '\n'.join([f'{{"n":{i}}}' for i in range(20)])
        f.write_text(lines, encoding="utf-8")
        monkeypatch.setattr(storage, "NOTIFICATIONS_FILE", f)
        result = storage._read_notifications(limit=5)
        assert len(result) == 5

    def test_skips_invalid_lines(self, monkeypatch, tmp_path):
        f = tmp_path / "notifications.jsonl"
        f.write_text('{"valid":true}\nbad_line', encoding="utf-8")
        monkeypatch.setattr(storage, "NOTIFICATIONS_FILE", f)
        result = storage._read_notifications()
        assert len(result) == 1


class TestAppendSnapshotHistory:
    def test_appends_line(self, monkeypatch, tmp_path):
        f = tmp_path / "snapshots.jsonl"
        monkeypatch.setattr(storage, "SNAPSHOT_HISTORY_FILE", f)
        storage._append_snapshot_history({"snap": 1})
        content = f.read_text(encoding="utf-8").strip()
        assert content


class TestReadSnapshotHistory:
    def test_no_file_returns_empty(self, monkeypatch):
        monkeypatch.setattr(storage, "SNAPSHOT_HISTORY_FILE", Path(f"/tmp/test_snap_{uuid.uuid4().hex}.json"))
        result = storage._read_snapshot_history()
        assert result == []

    def test_reads_lines(self, monkeypatch, tmp_path):
        f = tmp_path / "snapshots.jsonl"
        f.write_text('{"s":1}\n{"s":2}', encoding="utf-8")
        monkeypatch.setattr(storage, "SNAPSHOT_HISTORY_FILE", f)
        result = storage._read_snapshot_history()
        assert len(result) == 2

    def test_limits(self, monkeypatch, tmp_path):
        f = tmp_path / "snapshots.jsonl"
        f.write_text('\n'.join([f'{{"s":{i}}}' for i in range(2000)]), encoding="utf-8")
        monkeypatch.setattr(storage, "SNAPSHOT_HISTORY_FILE", f)
        result = storage._read_snapshot_history(limit=100)
        assert len(result) == 100

    def test_skips_invalid_lines(self, monkeypatch, tmp_path):
        f = tmp_path / "snapshots.jsonl"
        f.write_text('{"valid":true}\nbad_line', encoding="utf-8")
        monkeypatch.setattr(storage, "SNAPSHOT_HISTORY_FILE", f)
        result = storage._read_snapshot_history()
        assert len(result) == 1


class TestSaveSnapshotHistory:
    def test_saves_rows(self, monkeypatch, tmp_path):
        f = tmp_path / "snapshots.jsonl"
        monkeypatch.setattr(storage, "SNAPSHOT_HISTORY_FILE", f)
        rows = [{"s": i} for i in range(3)]
        storage._save_snapshot_history(rows)
        assert f.exists()
        loaded = storage._read_snapshot_history()
        assert len(loaded) == 3


class TestAppendIncidentHistory:
    def test_appends_to_existing_history(self):
        incident = {"history": [{"event": "old"}]}
        storage._append_incident_history(
            incident, event="new_event", actor_id="actor1",
            note="test note", metadata={"key": "val"},
        )
        assert len(incident["history"]) == 2
        assert incident["history"][1]["event"] == "new_event"
        assert incident["history"][1]["note"] == "test note"

    def test_adds_note_and_metadata(self):
        incident = {}
        storage._append_incident_history(
            incident, event="created", actor_id="system",
            note="Auto", metadata={"reason": "init"},
        )
        assert incident["history"][0]["note"] == "Auto"
        assert incident["history"][0]["metadata"]["reason"] == "init"

    def test_truncates_at_50(self):
        incident = {"history": [{"i": i} for i in range(60)]}
        storage._append_incident_history(incident, event="new", actor_id="sys")
        assert len(incident["history"]) == 50
